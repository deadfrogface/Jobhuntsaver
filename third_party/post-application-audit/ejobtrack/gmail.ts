import { htmlToText } from "html-to-text";

// ── Gmail API client ───────────────────────────────────────────────────────

const BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me";

// ── Rate-limit error ───────────────────────────────────────────────────────

export class RateLimitError extends Error {
	readonly retryAfter: string | undefined;

	constructor(message: string, retryAfter?: string) {
		super(message);
		this.name = "RateLimitError";
		this.retryAfter = retryAfter;
	}
}

/**
 * Fetch wrapper that auto-retries once on 401 after token refresh.
 */
async function fetchWithRetry(
	url: string,
	accessToken: string,
	options?: RequestInit,
	onUnauthorized?: () => Promise<string | null>,
): Promise<Response> {
	const headers = {
		Authorization: `Bearer ${accessToken}`,
		"Content-Type": "application/json",
		...(options?.headers || {}),
	};

	let res = await fetch(url, { ...options, headers });

	// 429 rate limit — throw immediately so callers can enqueue
	if (res.status === 429) {
		const retryAfter = res.headers.get("Retry-After") ?? undefined;
		const body = await res.text().catch(() => "rate limited");
		throw new RateLimitError(`Gmail API 429: ${body}`, retryAfter);
	}

	if (res.status === 401 && onUnauthorized) {
		const newToken = await onUnauthorized();
		if (newToken) {
			headers.Authorization = `Bearer ${newToken}`;
			res = await fetch(url, { ...options, headers });
		}
	}

	// Check 429 again after token refresh (unlikely but possible)
	if (res.status === 429) {
		const retryAfter = res.headers.get("Retry-After") ?? undefined;
		const body = await res.text().catch(() => "rate limited");
		throw new RateLimitError(`Gmail API 429: ${body}`, retryAfter);
	}

	return res;
}

// ── Types ──────────────────────────────────────────────────────────────────

export interface GmailMessageListItem {
	id: string;
	threadId: string;
}

export interface GmailMessageHeader {
	name: string;
	value: string;
}

export interface GmailMessagePart {
	mimeType: string;
	filename: string;
	headers: GmailMessageHeader[];
	body: { size: number; data?: string; attachmentId?: string };
	parts?: GmailMessagePart[];
}

export interface GmailMessage {
	id: string;
	threadId: string;
	labelIds: string[];
	snippet: string;
	payload: GmailMessagePart;
	internalDate: string;
	sizeEstimate: number;
}

export interface GmailListResponse {
	messages: GmailMessageListItem[];
	nextPageToken: string | null;
	resultSizeEstimate: number;
}

export interface ParsedEmail {
	id: string;
	threadId: string;
	subject: string;
	from: string;
	to: string;
	date: string;
	snippet: string;
	/** text/plain body (when available) or html-to-text of bodyHtml as fallback */
	body: string;
	bodyHtml?: string;
	/** html-to-text of bodyHtml — rich content even when text/plain is available */
	bodyClean?: string;
	bodyType: "text/plain" | "text/html" | "unknown";
	labelIds: string[];
	internalDate: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────

function getHeader(headers: GmailMessageHeader[], name: string): string {
	return (
		headers.find((h) => h.name.toLowerCase() === name.toLowerCase())?.value ??
		""
	);
}

function decodeBase64(data: string): string {
	try {
		const normalized = data.replace(/-/g, "+").replace(/_/g, "/");
		const padding = normalized.length % 4;
		const padded = padding ? normalized + "=".repeat(4 - padding) : normalized;
		// atob decodes to Latin-1, breaking UTF-8 chars.  Use Uint8Array + TextDecoder for proper UTF-8.
		const binary = atob(padded);
		const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
		return new TextDecoder().decode(bytes);
	} catch {
		return "";
	}
}

function extractBody(part: GmailMessagePart): {
	body: string;
	bodyHtml: string;
	bodyClean: string;
	type: "text/plain" | "text/html" | "unknown";
} {
	let textPlain = "";
	let textHtml = "";

	function walk(p: GmailMessagePart) {
		if (p.body?.data) {
			if (p.mimeType === "text/plain") {
				textPlain = decodeBase64(p.body.data);
			} else if (p.mimeType === "text/html") {
				textHtml = decodeBase64(p.body.data);
			}
		}
		if (p.parts) {
			for (const child of p.parts) walk(child);
		}
	}

	walk(part);

	const bodyClean = textHtml ? htmlToText(textHtml, { wordwrap: false }) : "";

	// Prefer rich HTML content (cleaned) over text/plain for display.
	// bodyClean is always available when HTML exists.
	if (bodyClean) {
		return {
			body: bodyClean,
			bodyHtml: textHtml,
			bodyClean,
			type: "text/html",
		};
	}

	if (textPlain) {
		return {
			body: textPlain,
			bodyHtml: textHtml,
			bodyClean: "",
			type: "text/plain",
		};
	}

	return { body: "", bodyHtml: "", bodyClean: "", type: "unknown" };
}

export function parseMessage(msg: GmailMessage): ParsedEmail {
	const headers = msg.payload.headers;
	const { body, bodyHtml, bodyClean, type } = extractBody(msg.payload);

	return {
		id: msg.id,
		threadId: msg.threadId,
		subject: getHeader(headers, "Subject"),
		from: getHeader(headers, "From"),
		to: getHeader(headers, "To"),
		date: getHeader(headers, "Date"),
		snippet: msg.snippet,
		body,
		bodyHtml: bodyHtml || undefined,
		bodyClean: bodyClean || undefined,
		bodyType: type,
		labelIds: msg.labelIds,
		internalDate: msg.internalDate,
	};
}

// ── API calls ──────────────────────────────────────────────────────────────

/** List message IDs with pagination. */
export async function listMessages(
	accessToken: string,
	opts: {
		maxResults?: number;
		pageToken?: string | null;
		q?: string;
		labelIds?: string[];
		onUnauthorized?: () => Promise<string | null>;
	} = {},
): Promise<GmailListResponse> {
	const params = new URLSearchParams();
	if (opts.maxResults) params.set("maxResults", String(opts.maxResults));
	if (opts.pageToken) params.set("pageToken", opts.pageToken);
	if (opts.q) params.set("q", opts.q);
	if (opts.labelIds?.length) {
		opts.labelIds.forEach((id) => params.append("labelIds", id));
	}

	const url = `${BASE_URL}/messages?${params.toString()}`;
	const res = await fetchWithRetry(
		url,
		accessToken,
		undefined,
		opts.onUnauthorized,
	);

	if (!res.ok) {
		const err = await res.text();
		throw new Error(`Gmail API list failed: ${res.status} — ${err}`);
	}

	const data = await res.json();
	return {
		messages: data.messages ?? [],
		nextPageToken: data.nextPageToken ?? null,
		resultSizeEstimate: data.resultSizeEstimate ?? 0,
	};
}

/** Get a single message (any format). */
export async function getMessage(
	accessToken: string,
	messageId: string,
	format: "full" | "metadata" | "minimal" | "raw" = "full",
	metadataHeaders?: string[],
	onUnauthorized?: () => Promise<string | null>,
): Promise<GmailMessage> {
	const params = new URLSearchParams({ format });
	if (metadataHeaders?.length) {
		metadataHeaders.forEach((h) => params.append("metadataHeaders", h));
	}
	const url = `${BASE_URL}/messages/${messageId}?${params.toString()}`;
	const res = await fetchWithRetry(url, accessToken, undefined, onUnauthorized);

	if (!res.ok) {
		const err = await res.text();
		throw new Error(`Gmail API get failed: ${res.status} — ${err}`);
	}

	return res.json() as Promise<GmailMessage>;
}
