import { expect, test } from '@playwright/test';

function isoDate(offsetDays: number) {
  const value = new Date();
  value.setDate(value.getDate() + offsetDays);
  return value.toISOString().slice(0, 10);
}

test('past due date is rejected and both draft fields survive reload', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('textbox', { name: 'Title' }).fill('Draft with date');
  await page.getByLabel('Due date').fill(isoDate(-2));
  await page.getByRole('button', { name: 'Add task' }).click();
  await expect(page.getByRole('alert')).toContainText('Due date cannot be in the past.');
  await page.reload();
  await expect(page.getByRole('textbox', { name: 'Title' })).toHaveValue('Draft with date');
  await expect(page.getByLabel('Due date')).toHaveValue(isoDate(-2));
});

test('valid due date submits and clears both persisted fields', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('textbox', { name: 'Title' }).fill('Future task');
  await page.getByLabel('Due date').fill(isoDate(3));
  await page.getByRole('button', { name: 'Add task' }).click();
  await expect(page.getByRole('heading', { name: 'Future task' })).toBeVisible();
  await page.reload();
  await expect(page.getByRole('textbox', { name: 'Title' })).toHaveValue('');
  await expect(page.getByLabel('Due date')).toHaveValue('');
});

