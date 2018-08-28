# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import messages, auth
from django.contrib.auth.decorators import login_required
from accounts.forms import UserRegistrationForm, UserLoginForm
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.template.context_processors import csrf
from django.conf import settings
import datetime
import stripe
import arrow


# Create your views here.

stripe.api_key = settings.STRIPE_SECRET


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Stripe Single payment
                # customer = stripe.Charge.create(
                #     amount=999,
                #     currency="GBP",
                #     description=form.cleaned_data['email'],
                #     card=form.cleaned_data['stripe_id'],
                # )

                # Stripe Subscription
                customer = stripe.Customer.create(
                    email=form.cleaned_data['email'],
                    # this is currently the card token/id
                    card=form.cleaned_data['stripe_id'],
                    plan='REG_MONTHLY',
                )

                # Stripe single Payment
                # if customer.paid:
                #     form.save()
                #     user = auth.authenticate(email=request.POST.get('email'),
                #                              password=request.POST.get('password1'))

                # Stripe Subscription
                if customer:
                    user = form.save()
                    user = auth.authenticate(email=request.POST.get('email'),
                                             password=request.POST.get('password1'))
                    user.stripe_id = customer.id
                    user.subscription_end = arrow.now().replace(weeks=+4).datetime
                    user.save()

                    if user:
                        auth.login(request, user)
                        messages.success(
                            request, "You have successfully registered")
                        return redirect(reverse('profile'))

                    else:
                        messages.error(
                            request, "unable to log you in at this time!")
                else:
                    messages.error(
                        request, "We were unable to take a payment with that card!")
            except stripe.error.CardError, e:
                messages.error(request, "Your card was declined!")
    else:
        today = datetime.date.today()
        form = UserRegistrationForm()

    args = {'form': form, 'publishable': settings.STRIPE_PUBLISHABLE}
    args.update(csrf(request))

    return render(request, 'register.html', args)


@login_required(login_url='/login')
def profile(request):
    return render(request, 'profile.html')


def login(request):
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            user = auth.authenticate(email=request.POST.get('email'),
                                     password=request.POST.get('password'))

            if user is not None:
                auth.login(request, user)
                messages.error(request, "You have successfully logged in")
                return redirect(reverse('profile'))
            else:
                form.add_error(
                    None, "Your email or password was not recognised")

    else:
        form = UserLoginForm()

    args = {'form': form}
    args.update(csrf(request))
    return render(request, 'login.html', args)


def logout(request):
    auth.logout(request)
    messages.success(request, 'You have successfully logged out')
    return redirect(reverse('index'))


@login_required(login_url='/accounts/login/')
def cancel_subscription(request):
    try:
        customer = stripe.Customer.retrieve(request.user.stripe_id)
        customer.cancel_subscription(at_period_end=True)
    except Exception, e:
        messages.error(request, e)
    return redirect('profile')
