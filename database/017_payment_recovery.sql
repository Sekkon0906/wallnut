CREATE INDEX coin_payments_recipient_requests ON coin_payment_requests (recipient_id, expires_at DESC, id DESC);
