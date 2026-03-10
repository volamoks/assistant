interface TemplateVariables {
    title: string;
    date: string;
    datetime: string;
    type: string;
    [key: string]: string | number | boolean | null | undefined;
}
declare function buildTemplateVariables(input?: Partial<TemplateVariables>, now?: Date): TemplateVariables;
declare function renderTemplate(template: string, variables: TemplateVariables): string;

export { type TemplateVariables, buildTemplateVariables, renderTemplate };
