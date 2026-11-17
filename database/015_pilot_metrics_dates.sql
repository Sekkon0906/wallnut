CREATE INDEX wallet_movements_report_date ON wallet_movements (created_at);
CREATE INDEX coin_payments_report_date ON coin_payment_requests (paid_at) WHERE paid_at IS NOT NULL;
CREATE INDEX grade_redemptions_report_date ON grade_redemptions (reviewed_at) WHERE status = 'approved';
CREATE INDEX ardy_purchases_report_date ON ardy_item_purchases (created_at);
CREATE INDEX ardy_nuts_report_date ON ardy_nuts (created_at);
