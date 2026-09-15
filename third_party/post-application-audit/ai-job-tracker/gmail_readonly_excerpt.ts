import {
  CATEGORY_TO_STATUS,
  TERMINAL_STATUSES,
  type JobStatus,
} from "@jobtrackr/core";
import { classifyEmail, aiAvailable } from "./ai";
import { getDb, getSetting, setSetting, deleteSetting } from "./db";
import { listJobs, matchJobForEmail, shouldAutoApply, updateJob } from "./jobs";

const SCOPE = "https://www.googleapis.com/auth/gmail.readonly";
const TOKEN_URL = "https://oauth2.googleapis.com/token";
const GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me";

/** Well-known ATS sender domains — emails from these are almost always hiring-related. */
const ATS_DOMAINS = [
  "greenhouse.io",
  "greenhouse-mail.io",
  "lever.co",
  "hire.lever.co",
  "ashbyhq.com",
  "myworkday.com",
  "myworkdayjobs.com",
  "icims.com",
  "smartrecruiters.com",
  "jobvite.com",
  "bamboohr.com",
  "workablemail.com",
  "recruitee.com",
  "breezy.hr",
  "rippling.com",
];

interface GmailTokens {
  access_token: string;
  refresh_token?: string;
  expires_at: number; // epoch ms
}

function creds() {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  if (!clientId || !clientSecret) return null;
  return { clientId, clientSecret };
}

function redirectUri(): string {
  const base = process.env.APP_URL || "http://localhost:3000";
  return `${base.replace(/\/$/, "")}/api/gmail/callback`;
}

export function gmailConfigured(): boolean {
  return creds() !== null;
}

export function gmailConnected(): boolean {
  return getSetting<GmailTokens>("gmailTokens") !== null;
}

export function disconnectGmail(): void {
  deleteSetting("gmailTokens");
  deleteSetting("gmailLastSyncAt");
}

export function buildAuthUrl(): string {
  const c = creds();
  if (!c) throw new Error("GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET not set");
  const params = new URLSearchParams({
    client_id: c.clientId,
    redirect_uri: redirectUri(),
    response_type: "code",
    scope: SCOPE,
    access_type: "offline",
    prompt: "consent",
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params}`;
}

export async function exchangeCode(code: string): Promise<void> {
  const c = creds();
  if (!c) throw new Error("Google OAuth credentials not configured");
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: c.clientId,
      client_secret: c.clientSecret,
      redirect_uri: redirectUri(),
      grant_type: "authorization_code",
    }),
  });
  if (!res.ok) throw new Error(`Token exchange failed: ${await res.text()}`);
  const data = (await res.json()) as {
    access_token: string;
    refresh_token?: string;
    expires_in: number;
  };
  setSetting("gmailTokens", {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Date.now() + data.expires_in * 1000,
  } satisfies GmailTokens);
}

async function getAccessToken(): Promise<string> {
  const tokens = getSetting<GmailTokens>("gmailTokens");
  if (!tokens) throw new Error("Gmail is not connected");
  if (Date.now() < tokens.expires_at - 60_000) return tokens.access_token;

  const c = creds();
  if (!c || !tokens.refresh_token) {
    throw new Error("Gmail token expired and cannot be refreshed — reconnect Gmail");
  }
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "content-type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      client_id: c.clientId,
      client_secret: c.clientSecret,
      refresh_token: tokens.refresh_token,
