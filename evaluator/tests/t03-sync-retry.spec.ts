import { expect, test } from '@playwright/test';

test('retry moves error through loading to success without losing selection', async ({ page }) => {
  await page.goto('/?sync=error');
  await page.getByRole('button', { name: 'Polish empty states Ravi · In progress' }).click();
  await expect(page.getByRole('alert')).toContainText('Sync failed');
  await page.getByRole('button', { name: 'Retry sync' }).click();
  await expect(page.getByText('Checking service…')).toBeVisible();
  await expect(page.getByText('All changes are synced.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry sync' })).toBeHidden();
  await expect(page.getByRole('heading', { name: 'Polish empty states' })).toBeVisible();
});

test('normal success path still has no retry action', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('All changes are synced.')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Retry sync' })).toHaveCount(0);
});
