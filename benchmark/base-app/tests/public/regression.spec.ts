import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.goto('/');
});

test('selecting a task updates the detail card', async ({ page }) => {
  await page.getByRole('button', { name: 'Polish empty states Ravi · In progress' }).click();
  await expect(page.getByRole('heading', { name: 'Polish empty states' })).toBeVisible();
  await expect(page.getByText('Ravi', { exact: true })).toBeVisible();
});

test('Escape closes the editor and restores focus to its edit button', async ({ page }) => {
  const edit = page.getByRole('button', { name: 'Edit Audit keyboard navigation' });
  await edit.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toBeHidden();
  await expect(edit).toBeFocused();
});

test('cancelling an edit does not change the task', async ({ page }) => {
  await page.getByRole('button', { name: 'Edit Audit keyboard navigation' }).click();
  await page.getByRole('dialog').getByLabel('Title').fill('Changed but cancelled');
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByRole('heading', { name: 'Audit keyboard navigation' })).toBeVisible();
});

test('mobile navigation opens and closes', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  const menu = page.getByRole('button', { name: 'Menu' });
  await expect(menu).toHaveAttribute('aria-expanded', 'false');
  await menu.click();
  await expect(menu).toHaveAttribute('aria-expanded', 'true');
  await expect(page.getByRole('link', { name: 'Board' })).toBeVisible();
  await menu.click();
  await expect(page.getByRole('link', { name: 'Board' })).toBeHidden();
});

test('new-task draft survives reload and clears after a successful add', async ({ page }) => {
  const title = page.getByRole('textbox', { name: 'Title' });
  await title.fill('Remember this draft');
  await page.reload();
  await expect(page.getByRole('textbox', { name: 'Title' })).toHaveValue('Remember this draft');
  await page.getByRole('button', { name: 'Add task' }).click();
  await expect(page.getByRole('heading', { name: 'Remember this draft' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('textbox', { name: 'Title' })).toHaveValue('');
});

test('sync success state replaces the loading state', async ({ page }) => {
  await expect(page.getByText('All changes are synced.')).toBeVisible();
  await expect(page.getByText('Checking service…')).toBeHidden();
});
