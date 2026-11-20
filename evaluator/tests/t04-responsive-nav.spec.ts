import { expect, test } from '@playwright/test';

test('desktop exposes the new destination and tracks the active section', async ({ page }) => {
  await page.setViewportSize({ width: 1100, height: 800 });
  await page.goto('/');
  const reports = page.getByRole('link', { name: 'Reports' });
  await expect(reports).toBeVisible();
  await reports.click();
  await expect(reports).toHaveAttribute('aria-current', 'page');
  await expect(page).toHaveURL(/#reports$/);
  await expect(page.getByRole('link', { name: 'Board' })).not.toHaveAttribute('aria-current', 'page');
});

test('mobile selection closes the menu and desktop layout returns after resize', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 800 });
  await page.goto('/');
  const menu = page.getByRole('button', { name: 'Menu' });
  await menu.click();
  await page.getByRole('link', { name: 'Reports' }).click();
  await expect(menu).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('link', { name: 'Board' })).toBeHidden();
  await page.setViewportSize({ width: 1100, height: 800 });
  await expect(page.getByRole('link', { name: 'Board' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Activity' })).toBeVisible();
});

