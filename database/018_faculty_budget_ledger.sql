CREATE INDEX point_allocations_faculty_history ON point_allocations (faculty_id, created_at DESC, id DESC);
CREATE INDEX wallet_movements_faculty_history ON wallet_movements (faculty_id, created_at DESC, id DESC);
