import { expect, test } from '@playwright/test';

test('saving a priority updates the selected task', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Edit Audit keyboard navigation' }).click();
  await page.getByLabel('Priority').selectOption('Low');
  await page.getByRole('button', { name: 'Save changes' }).click();
  const detail = page.getByRole('heading', { name: 'Audit keyboard navigation' }).locator('..');
  await expect(detail).toContainText('Low');
});

test('cancel and Escape discard priority edits while focus restoration survives', async ({ page }) => {
  await page.goto('/');
  const edit = page.getByRole('button', { name: 'Edit Audit keyboard navigation' });
  await edit.click();
  await page.getByLabel('Priority').selectOption('Low');
  await page.getByRole('button', { name: 'Cancel' }).click();
  await expect(page.getByText('High', { exact: true })).toBeVisible();

  await edit.click();
  await page.getByLabel('Priority').selectOption('Medium');
  await page.keyboard.press('Escape');
  await expect(page.getByText('High', { exact: true })).toBeVisible();
  await expect(edit).toBeFocused();
});

