import { logger } from "./logger";

export type ModelStatus = "unloaded" | "loading" | "ready" | "error";

type ClassifyFn = (text: string) => Promise<{ label: string; score: number }[]>;

type StatusCallback = (status: ModelStatus) => void;

let _classify: ClassifyFn | null = null;
let _loading = false;
let _erred: string | null = null;
let _status: ModelStatus = "unloaded";
const _listeners = new Set<StatusCallback>();

function notifyListeners(): void {
	for (const cb of _listeners) cb(_status);
}

/** Get current ML model load status. */
export function getModelStatus(): ModelStatus {
	return _status;
}

/**
 * Subscribe to model status changes.
 * Returns an unsubscribe function.
 */
export function onModelStatusChange(cb: StatusCallback): () => void {
	_listeners.add(cb);
	// Immediately notify with current status
	cb(_status);
	return () => _listeners.delete(cb);
}

/** Get model load error message, if any. Null means model loaded or still loading. */
export function getModelError(): string | null {
	return _erred;
}

/** Labels that indicate a job-related email. */
const JOB_LABELS = new Set(["confirmation", "rejection", "interview", "offer"]);

async function load(): Promise<void> {
	if (_classify || _loading) {
		logger.log("classify-email", "load() skipped — already loading or loaded");
		return;
	}
	_loading = true;
	_status = "loading";
	notifyListeners();
	logger.log(
		"classify-email",
		"load() starting — importing @xenova/transformers",
	);
	try {
		const startMs = Date.now();
		const transformers = await import("@xenova/transformers");
		const { pipeline, env } = transformers;
		logger.log(
			"classify-email",
			"@xenova/transformers imported in",
			Date.now() - startMs,
			"ms",
		);
		logger.log("classify-email", "default remoteHost:", env.remoteHost);
		logger.log(
			"classify-email",
			"default remotePathTemplate:",
			env.remotePathTemplate,
		);
		logger.log("classify-email", "default localModelPath:", env.localModelPath);
		logger.log(
			"classify-email",
			"default allowLocalModels:",
			env.allowLocalModels,
		);

		// Disable local model loading — Vite dev server returns HTML for
		// missing /models/ files, which the library caches as model data.
		env.allowLocalModels = false;
		logger.log("classify-email", "set allowLocalModels to false");

		const pipelineStart = Date.now();
		logger.log(
			"classify-email",
			"calling pipeline('text-classification', 'mattohan/job-tracker-email-classifier')",
		);
		const pipe = await pipeline(
			"text-classification",
			"mattohan/job-tracker-email-classifier",
		);
		logger.log(
			"classify-email",
			"pipeline() completed in",
			Date.now() - pipelineStart,
			"ms",
		);

		_classify = pipe as unknown as ClassifyFn;
		_status = "ready";
		logger.log("classify-email", "model ready — classifyEmail will now use ML");
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err);
		const stack = err instanceof Error ? err.stack : "";
		_erred = msg;
		_status = "error";
		logger.error("classify-email", "model load failed:", msg);
		logger.error("classify-email", "stack:", stack);

		// Clear stale transformers cache — corrupted entries (e.g. Vite 404
		// HTML cached as model data) prevent retries from succeeding.
		try {
			await caches.delete("transformers-cache");
			logger.log("classify-email", "cleared transformers-cache for next retry");
		} catch {
			logger.warn("classify-email", "failed to clear transformers-cache");
		}
	} finally {
		_loading = false;
		notifyListeners();
		logger.log(
			"classify-email",
			"load() finished. _status:",
			_status,
			"_erred:",
			_erred,
		);
	}
}

/**
 * Classify an email as job-related or not.
 *
 * Returns:
 *   - `true`  → model says job email
 *   - `false` → model says not a job email
 *   - `null`  → model not loaded yet (caller should fall back to keyword matching)
 */
export async function classifyEmail(
	subject: string,
	body: string,
): Promise<boolean | null> {
	// First call — trigger lazy load, fall back to keywords
	if (!_classify && !_loading && !_erred) {
		load();
		return null;
	}

	if (!_classify) return null; // Still loading or errored — fall back

	try {
		// ponytail: strip URLs (HTML email bodies carry image URLs that eat
		// the char budget) + wider window — rejection text often lands after
		// salutation + "thank you for applying" preamble
		const text = `${subject}\n${body}`
			.replace(/https?:\/\/\S+/g, "")
			.slice(0, 1024);
		const result = await _classify(text);
		logger.log(
			"classify-test",
			`sub: ${subject} |||| label: ${result[0].label}`,
		);
		return JOB_LABELS.has(result[0].label);
	} catch {
		return null; // Inference failed — fall back
	}
}
