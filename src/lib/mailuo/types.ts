export type MailuoSearchMode = 'hybrid' | 'keyword' | 'semantic';
export type MailuoSearchSort = 'relevance' | 'updated_desc' | 'updated_asc';
export type MailuoIntent = 'search' | 'answer';

export type MailuoKnowledge = {
	id: string;
	name: string;
	description: string;
};

export type MailuoSourceFacet = {
	source: string;
	display_name: string;
	color?: string | null;
	object_count: number;
};

export type MailuoSnippet = {
	chunk_no: number;
	content: string;
	matched_by: string[];
};

export type MailuoObjectResult = {
	knowledge_ids: string[];
	source: string;
	source_object_id: string;
	title: string;
	source_url: string;
	source_updated_at: string;
	metadata: Record<string, unknown>;
	matched_by: string[];
	matches: MailuoSnippet[];
};

export type MailuoSearchRequest = {
	query: string;
	mode: MailuoSearchMode;
	knowledge_ids?: string[];
	sources?: string[];
	limit: number;
	sort?: MailuoSearchSort;
};

export type MailuoAnswerRequest = Omit<MailuoSearchRequest, 'limit'> & {
	model: string;
	history?: MailuoConversationMessage[];
};

export type MailuoConversationMessage = {
	role: 'user' | 'assistant';
	content: string;
};

export type MailuoSearchResponse = {
	requested_mode: MailuoSearchMode;
	executed_mode: MailuoSearchMode;
	degraded: boolean;
	warnings: string[];
	results: MailuoObjectResult[];
};

export type MailuoAnswerTurn = {
	question: string;
	content: string;
	results: MailuoObjectResult[];
	mode: MailuoSearchMode;
};

export type MailuoFacetResponse = {
	sources: MailuoSourceFacet[];
};

export type MailuoQueryState = {
	query: string;
	mode: MailuoSearchMode;
	sort: MailuoSearchSort;
	knowledgeIds: string[];
	sources: string[];
};
