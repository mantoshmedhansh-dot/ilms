-- ============================================================
-- MIGRATION PART 5: NOTIFICATIONS TABLES
-- Run AFTER Part 1 (enum types)
-- ============================================================

-- Notifications table
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    notification_type notificationtype NOT NULL,
    priority notificationpriority DEFAULT 'MEDIUM',

    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,

    action_url VARCHAR(500),
    action_label VARCHAR(100),

    entity_type VARCHAR(50),
    entity_id UUID,

    extra_data JSONB DEFAULT '{}',

    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP,

    channels JSONB DEFAULT '[]',
    delivered_at JSONB DEFAULT '{}',

    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);
CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(notification_type);
CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_notifications_user_type ON notifications(user_id, notification_type);
CREATE INDEX IF NOT EXISTS idx_notifications_created ON notifications(created_at);

-- Notification Preferences table
CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    push_enabled BOOLEAN DEFAULT TRUE,
    in_app_enabled BOOLEAN DEFAULT TRUE,

    type_preferences JSONB DEFAULT '{}',

    quiet_hours_enabled BOOLEAN DEFAULT FALSE,
    quiet_hours_start VARCHAR(5),
    quiet_hours_end VARCHAR(5),

    email_digest_enabled BOOLEAN DEFAULT FALSE,
    email_digest_frequency VARCHAR(20) DEFAULT 'DAILY',

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_preferences_user ON notification_preferences(user_id);

-- Notification Templates table
CREATE TABLE IF NOT EXISTS notification_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    notification_type notificationtype UNIQUE NOT NULL,

    title_template VARCHAR(200) NOT NULL,
    message_template TEXT NOT NULL,

    email_subject_template VARCHAR(200),
    email_body_template TEXT,
    sms_template VARCHAR(500),

    default_channels JSONB DEFAULT '["IN_APP"]',
    default_priority notificationpriority DEFAULT 'MEDIUM',

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Announcements table
CREATE TABLE IF NOT EXISTS announcements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,

    announcement_type VARCHAR(20) DEFAULT 'INFO',

    action_url VARCHAR(500),
    action_label VARCHAR(100),

    target_roles JSONB DEFAULT '[]',
    target_departments JSONB DEFAULT '[]',

    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,

    is_dismissible BOOLEAN DEFAULT TRUE,
    show_on_dashboard BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,

    created_by_id UUID REFERENCES users(id) ON DELETE SET NULL,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_announcements_active ON announcements(is_active);
CREATE INDEX IF NOT EXISTS idx_announcements_dates ON announcements(start_date, end_date);

-- Announcement Dismissals table
CREATE TABLE IF NOT EXISTS announcement_dismissals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    announcement_id UUID NOT NULL REFERENCES announcements(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    dismissed_at TIMESTAMP DEFAULT NOW(),

    UNIQUE(announcement_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_announcement_dismissals_announcement ON announcement_dismissals(announcement_id);
CREATE INDEX IF NOT EXISTS idx_announcement_dismissals_user ON announcement_dismissals(user_id);

SELECT 'Part 5: Notifications tables created successfully!' AS result;
