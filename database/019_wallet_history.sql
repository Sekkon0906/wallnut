CREATE INDEX ardy_purchases_history ON ardy_item_purchases (student_id, created_at DESC, id DESC);
CREATE INDEX grade_redemptions_history ON grade_redemptions (student_id, reviewed_at DESC, id DESC)
    WHERE status = 'approved';
CREATE INDEX coin_payments_sent_history ON coin_payment_requests (payer_id, paid_at DESC, id DESC)
    WHERE paid_at IS NOT NULL;
CREATE INDEX coin_payments_received_history ON coin_payment_requests (recipient_id, paid_at DESC, id DESC)
    WHERE paid_at IS NOT NULL;
