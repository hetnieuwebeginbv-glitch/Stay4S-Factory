CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE agent_register (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    template_id TEXT NOT NULL,
    system_prompt TEXT NOT NULL,
    tool_scopes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','paused','retired')),
    spawned_by TEXT NOT NULL,
    spawned_reason TEXT,
    max_jobs_per_hour INTEGER NOT NULL DEFAULT 20,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE opdrachten (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wa_id TEXT NOT NULL,
    wamid TEXT UNIQUE,
    raw_text TEXT NOT NULL,
    intent TEXT,
    plan_json JSONB,
    assigned_agent TEXT,
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued','running','done','failed','rejected')),
    result_text TEXT,
    error_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);
CREATE INDEX opdrachten_wa_id_idx ON opdrachten (wa_id, created_at DESC);
CREATE TABLE infovault (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    source TEXT,
    agent_slug TEXT,
    opdracht_id UUID REFERENCES opdrachten(id),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE tool_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_slug TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL,
    outcome TEXT NOT NULL,
    http_status INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE conversation_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wa_id TEXT NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    summary TEXT NOT NULL,
    token_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO agent_register (slug, display_name, template_id, system_prompt, tool_scopes, spawned_by, spawned_reason) VALUES
('hoofdagent','Stay4S Hoofdagent','hoofd','Je plant en delegeert. Geen GitHub-writes.',ARRAY['spawn_specialist','enqueue_job','vault_write','vault_search'],'bootstrap','system'),
('pr-reviewer','GitHub PR Reviewer','pr_reviewer','Zie agents/pr_reviewer/SYSTEM.md',ARRAY['github_list_repos','github_list_pulls','github_get_pr','github_list_files'],'bootstrap','default');
