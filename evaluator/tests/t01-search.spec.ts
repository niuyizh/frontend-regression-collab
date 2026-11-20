import { expect, test } from '@playwright/test';

test('search filters case-insensitively and exposes an empty state', async ({ page }) => {
  await page.goto('/');
  const search = page.getByRole('searchbox', { name: 'Search tasks' });
  await search.fill('POLISH');
  await expect(page.getByText('Polish empty states', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Audit keyboard navigation Mina · Todo' })).toBeHidden();
  await search.fill('not present');
  await expect(page.getByText('No tasks match your search.')).toBeVisible();
});

test('filtering does not discard selection and clear restores the list', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Polish empty states Ravi · In progress' }).click();
  await page.getByRole('searchbox', { name: 'Search tasks' }).fill('Audit');
  await expect(page.getByRole('heading', { name: 'Polish empty states' })).toBeVisible();
  await page.getByRole('button', { name: 'Clear search' }).click();
  await expect(page.getByRole('button', { name: 'Polish empty states Ravi · In progress' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Clear search' })).toBeFocused();
});
