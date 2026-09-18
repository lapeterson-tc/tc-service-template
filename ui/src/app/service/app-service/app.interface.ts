export interface AppConfig {
    /** True when the Bedrock boot preflight succeeded; gates every AI surface. */
    bedrock: boolean;
    /**
     * NOTE: /api/tc/app-config serializes with by_alias=false, so multi-word
     * fields arrive **snake_case**. Do NOT "correct" these to camelCase —
     * they will silently read as undefined and quietly disable the feature
     * they gate.
     */
    schema_version: string;
    ui: {
        title: string;
        version: string;
    };
}
