import { describe, expect, it } from 'vitest';
import { listQuery, withFilter, withPage } from './listParams';

describe('list parameters in the URL', () => {
  it('passes page, page_size, sort and the known filters as they are', () => {
    const search = new URLSearchParams('page=3&page_size=500&sort=-name&search=caja&other=x');
    expect(listQuery(search, ['search', 'is_active'])).toEqual({
      page: '3',
      page_size: '500',
      sort: '-name',
      search: 'caja',
    });
  });

  it('changing a filter goes back to page 1', () => {
    const next = withFilter(new URLSearchParams('page=4&search=a'), 'search', 'b');
    expect(next.toString()).toBe('search=b');
  });

  it('clearing a filter removes it', () => {
    expect(withFilter(new URLSearchParams('search=a&page=2'), 'search', '').toString()).toBe('');
  });

  it('page 1 is not written in the URL', () => {
    expect(withPage(new URLSearchParams('page=4&sort=sku'), 1).toString()).toBe('sort=sku');
    expect(withPage(new URLSearchParams('sort=sku'), 2).toString()).toBe('sort=sku&page=2');
  });
});
