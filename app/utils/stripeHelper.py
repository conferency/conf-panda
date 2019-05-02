# -*- coding: utf-8 -*-
"""Hepler functions for stripe."""


import stripe


def generate_customer(email, name, source):
    """Generate Customer and return id."""
    try:
        return stripe.Customer.create(description=name,
                                      email=email,
                                      source=source).id
    except stripe.error.StripeError as e:
        raise e


def charge(customer_id, amount, description, currency='USD'):
    """Generate charge and return id."""
    try:
        charge = stripe.Charge.create(
            customer=customer_id,
            amount=int(round(amount * 100)),
            currency=currency,
            description=description
        )
        if charge:
            return charge.id, charge.balance_transaction
        else:
            raise Exception('Cannot find the charge')
    except stripe.error.StripeError as e:
        raise e


def refund(charge_id):
    """Refund a transaction."""
    try:
        refund = stripe.Refund.create(charge=charge_id)
    except stripe.error.InvalidRequestError as e:
        raise e
    if refund.status == 'succeeded':
        return refund.id


def get_net(balance_transaction_id):
    """Return net of a charge."""
    try:
        balance_transaction = stripe.BalanceTransaction.retrieve(
            balance_transaction_id)
        if balance_transaction:
            return balance_transaction.net / 100.0, balance_transaction.amount / 100.0
        else:
            raise Exception('Cannot find the blance transaction')
    except stripe.error.StripeError as e:
        raise e
