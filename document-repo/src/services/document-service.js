import { downloadData } from 'aws-amplify/storage';

/**
 * Custom error for documents not found in S3.
 */
export class DocumentNotFoundError extends Error {
  constructor(path) {
    super(`Document not found: ${path}`);
    this.name = 'DocumentNotFoundError';
    this.path = path;
  }
}

/**
 * Custom error for network failures during S3 retrieval.
 */
export class NetworkError extends Error {
  constructor(message) {
    super(message || 'Network error: unable to reach the document service');
    this.name = 'NetworkError';
  }
}

/**
 * Converts a URL path to an S3 object key by appending `.md`.
 * @param {string} path - URL path (e.g., "guides/setup")
 * @returns {string} S3 key (e.g., "guides/setup.md")
 */
export function pathToS3Key(path) {
  const cleanPath = path.replace(/\/+$/, '');
  return `${cleanPath}.md`;
}

/**
 * Converts an S3 object key back to a URL path by stripping `.md`.
 * @param {string} key - S3 key (e.g., "guides/setup.md")
 * @returns {string} URL path (e.g., "guides/setup")
 */
export function s3KeyToPath(key) {
  return key.replace(/\.md$/, '');
}

/**
 * Fetches a markdown document from S3 via Amplify Storage.
 * @param {string} path - The document path (e.g., "my-document" or "guides/setup")
 * @returns {Promise<string>} The raw markdown content
 * @throws {DocumentNotFoundError} If the document doesn't exist in S3
 * @throws {NetworkError} If S3 is unreachable
 */
export async function fetchDocument(path) {
  const key = pathToS3Key(path);

  try {
    const result = await downloadData({ key }).result;
    const text = await result.body.text();
    return text;
  } catch (error) {
    if (
      error?.name === 'NoSuchKey' ||
      error?.$metadata?.httpStatusCode === 404 ||
      error?.message?.includes('NoSuchKey') ||
      error?.message?.includes('404')
    ) {
      throw new DocumentNotFoundError(path);
    }

    if (
      error?.message?.includes('Network') ||
      error?.message?.includes('Failed to fetch') ||
      error?.name === 'NetworkError' ||
      !navigator.onLine
    ) {
      throw new NetworkError(error?.message);
    }

    throw error;
  }
}
