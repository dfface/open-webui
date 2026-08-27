import { readFileSync } from 'node:fs';

import { describe, expect, it } from 'vitest';

describe('Mailuo sidebar entry', () => {
	it('keeps 脉络 in the primary sidebar instead of only the user menu', () => {
		const sidebar = readFileSync(new URL('./Sidebar.svelte', import.meta.url), 'utf8');
		const userMenu = readFileSync(new URL('./Sidebar/UserMenu.svelte', import.meta.url), 'utf8');

		expect(sidebar.match(/href="\/mailuo"/g)).toHaveLength(2);
		expect(sidebar.match(/aria-label="脉络"/g)).toHaveLength(2);
		expect(userMenu).not.toContain('href="/mailuo"');
	});
});
