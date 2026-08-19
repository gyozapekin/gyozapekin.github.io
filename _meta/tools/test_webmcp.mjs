/**
 * webmcp.js の検証テスト（Playwright）
 *
 * 実行: node tools/test_webmcp.mjs
 * コード変更後は必ずこれを流す。
 *
 * ブラウザにまだWebMCPが載っていないので、document.modelContext を差し替えた
 * スタブで登録と実行を再現し、ツールの中身を検証する。
 */
import { chromium } from 'playwright';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.dirname(HERE);
const DATA_SRC = path.resolve(ROOT, '../phase0_geo/dist/public_data');

let pass = 0;
const fails = [];
function check(cond, label) {
  if (cond) { pass++; console.log('  ok  ' + label); }
  else { fails.push(label); console.log('  NG  ' + label); }
}

/* ------------------------------------------------------------- 準備 */

const page_html = (title, extra = '') => `<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><title>${title}</title></head>
<body><h1>${title}</h1>${extra}
<script defer src="/assets/js/webmcp.js"></script>
</body></html>`;

const files = {
  '/index.html': page_html('ホーム'),
  '/menu.html': page_html('メニュー'),
  '/order.html': page_html('ネットショップ'),
  '/about.html': page_html('店舗紹介'),
  '/howto.html': page_html('餃子の焼き方'),
  '/assets/js/webmcp.js': fs.readFileSync(path.join(ROOT, 'assets/js/webmcp.js'), 'utf8'),
};
for (const n of ['shop', 'menu', 'products', 'faq']) {
  files['/data/' + n + '.json'] = fs.readFileSync(path.join(DATA_SRC, n + '.json'), 'utf8');
}

const server = http.createServer((req, res) => {
  const url = req.url.split('?')[0];
  const body = files[url] ?? files[url + 'index.html'];
  if (body === undefined) { res.writeHead(404); res.end('not found'); return; }
  const type = url.endsWith('.json') ? 'application/json'
    : url.endsWith('.js') ? 'text/javascript' : 'text/html';
  res.writeHead(200, { 'content-type': type + '; charset=utf-8' });
  res.end(body);
});
await new Promise(r => server.listen(0, '127.0.0.1', r));
const BASE = 'http://127.0.0.1:' + server.address().port;

/* --------------------------------------------------- スタブとヘルパー */

// 実際のブラウザにはまだ modelContext がないので、登録を受け止めるスタブを入れる
const STUB = `
window.__registered = [];
document.modelContext = {
  registerTool: function (t) {
    if (window.__registered.some(x => x.name === t.name)) {
      throw new DOMException('duplicate', 'InvalidStateError');
    }
    window.__registered.push(t);
  },
  unregisterTool: function (name) {
    window.__registered = window.__registered.filter(x => x.name !== name);
  }
};
`;

const CAL_PRIMARY = 'https://pekin-shift-default-rtdb.asia-southeast1.firebasedatabase.app/**';
const CAL_FIXTURE = {
  pekin_settings: {
    defaultClosedDays: [2, 3],
    specialDates: {
      '2026-08-20': { type: 'closed', label: '臨時休業' },
      '2026-08-25': { type: 'open', label: '営業' }
    }
  }
};

async function newPage(browser, { calendar = CAL_FIXTURE, stub = true, killCalendar = false } = {}) {
  const ctx = await browser.newContext();
  if (stub) await ctx.addInitScript(STUB);
  await ctx.route(CAL_PRIMARY, route => {
    if (killCalendar) return route.abort();
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(calendar) });
  });
  await ctx.route('**/shift/db.json', route => killCalendar ? route.abort()
    : route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(calendar) }));
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  page.__errors = errors;
  return page;
}

const call = (page, name, input = {}) => page.evaluate(async ([n, i]) => {
  const t = window.__registered.find(x => x.name === n);
  if (!t) return { missing: true };
  const res = await t.execute(i);
  const text = res && res.content && res.content[0] ? res.content[0].text : null;
  return { isError: !!(res && res.isError), data: text ? JSON.parse(text) : null };
}, [name, input]);

/* ------------------------------------------------------------- 実行 */

const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium' });

console.log('\n[1] ページごとのツール登録');
{
  const expected = {
    '/index.html': ['get_shop_info', 'check_open_day', 'search_menu', 'list_takeout_items'],
    '/menu.html': ['get_shop_info', 'check_open_day', 'search_menu'],
    '/order.html': ['get_shop_info', 'check_open_day', 'list_takeout_items'],
    '/about.html': ['get_shop_info', 'check_open_day'],
    '/howto.html': ['get_shop_info', 'check_open_day'],
  };
  for (const [url, names] of Object.entries(expected)) {
    const page = await newPage(browser);
    await page.goto(BASE + url);
    const got = await page.evaluate(() => window.__registered.map(t => t.name));
    check(JSON.stringify(got) === JSON.stringify(names), `${url} で ${names.join(', ')} が登録される`);
    const meta = await page.evaluate(() => window.__pekinWebMCP);
    check(meta && meta.registered === names.length, `${url} の登録件数が記録される`);
    check(page.__errors.length === 0, `${url} でJSエラーが出ない`);
    await page.context().close();
  }
}

console.log('\n[2] 非対応ブラウザでは何もしない');
{
  const page = await newPage(browser, { stub: false });
  await page.goto(BASE + '/index.html');
  const state = await page.evaluate(() => ({
    meta: window.__pekinWebMCP || null,
    hasTools: !!window.__pekinWebMCPTools,
    title: document.title
  }));
  check(state.meta === null, 'modelContextが無ければ登録しない');
  check(state.hasTools === true, 'ツール定義自体は読み込まれている（検証用）');
  check(state.title === 'ホーム', 'ページは通常どおり表示される');
  check(page.__errors.length === 0, '非対応でもJSエラーが出ない');
  await page.context().close();
}

console.log('\n[3] 各ツールのスキーマ');
{
  const page = await newPage(browser);
  await page.goto(BASE + '/index.html');
  const tools = await page.evaluate(() => window.__registered.map(t => ({
    name: t.name, desc: (t.description || '').length,
    schema: !!(t.inputSchema && t.inputSchema.type === 'object'),
    readOnly: !!(t.annotations && t.annotations.readOnlyHint),
    exec: typeof t.execute
  })));
  for (const t of tools) {
    check(t.desc > 40, `${t.name}: 説明文が十分な長さ`);
    check(t.schema, `${t.name}: inputSchemaがobject`);
    check(t.readOnly, `${t.name}: readOnlyHintがtrue（副作用なし）`);
    check(t.exec === 'function', `${t.name}: executeが関数`);
  }
  await page.context().close();
}

console.log('\n[4] get_shop_info');
{
  const page = await newPage(browser);
  await page.goto(BASE + '/index.html');
  const r = await call(page, 'get_shop_info');
  check(!r.isError, 'エラーにならない');
  check(r.data.name === '海鮮餃子 北京', '店名が正しい');
  check(r.data.telephone === '072-849-0433', '電話番号が正しい');
  check(r.data.closedDays === '火曜日（水曜日は不定休）', '定休日表記が社長方針どおり');
  check(r.data.hours === '11:30〜22:00' && r.data.lastOrder === '21:30', '営業時間とラストオーダー');
  check(/宮之阪/.test(r.data.address) && /573-0022/.test(r.data.address), '住所に郵便番号と町名');
  check(r.data.onlineReservation === false, 'オンライン予約は不可と答える');
  check(r.data.nationwideShipping === true, '全国発送は可と答える');
  check(Array.isArray(r.data.sameAs) && r.data.sameAs.length >= 5, 'SNSなどのリンクを返す');
  await page.context().close();
}

console.log('\n[5] check_open_day');
{
  const page = await newPage(browser);
  await page.goto(BASE + '/index.html');
  const tue = await call(page, 'check_open_day', { date: '2026-08-18' });
  check(tue.data.isOpen === false && /定休日/.test(tue.data.reason), '火曜は定休日で休み');
  const wed = await call(page, 'check_open_day', { date: '2026-08-19' });
  check(wed.data.isOpen === false && /不定休/.test(wed.data.reason), '水曜は不定休で休み');
  const fri = await call(page, 'check_open_day', { date: '2026-08-21' });
  check(fri.data.isOpen === true && fri.data.hours === '11:30〜22:00', '金曜は営業日で時間も返す');
  const rinji = await call(page, 'check_open_day', { date: '2026-08-20' });
  check(rinji.data.isOpen === false && /臨時休業/.test(rinji.data.reason), '臨時休業を反映する');
  const rinjiOpen = await call(page, 'check_open_day', { date: '2026-08-25' });
  check(rinjiOpen.data.isOpen === true && /臨時営業/.test(rinjiOpen.data.reason),
    '火曜でも臨時営業なら営業と答える');
  const today = await call(page, 'check_open_day', {});
  check(today.data && typeof today.data.isOpen === 'boolean', '日付省略で今日を判定する');
  const bad = await call(page, 'check_open_day', { date: '2026-13-45' });
  check(bad.isError === true, '不正な日付はエラーを返す');
  const bad2 = await call(page, 'check_open_day', { date: 'あした' });
  check(bad2.isError === true, '日本語の日付表現はエラーを返す（推測しない）');
  await page.context().close();
}

console.log('\n[6] カレンダーが取れないときのフォールバック');
{
  const page = await newPage(browser, { killCalendar: true });
  await page.goto(BASE + '/index.html');
  const tue = await call(page, 'check_open_day', { date: '2026-08-18' });
  check(tue.data && tue.data.isOpen === false, 'Firebaseが落ちてもshop.jsonの休業曜日で判定できる');
  const fri = await call(page, 'check_open_day', { date: '2026-08-21' });
  check(fri.data && fri.data.isOpen === true, 'フォールバック時も営業日は営業と答える');
  await page.context().close();
}

console.log('\n[7] search_menu');
{
  const page = await newPage(browser);
  await page.goto(BASE + '/menu.html');
  const all = await call(page, 'search_menu', { limit: 200 });
  check(all.data.total === 107, '全107品が対象');
  check(all.data.categories.length === 10, 'カテゴリは10種');
  const gyoza = await call(page, 'search_menu', { query: '餃子' });
  check(gyoza.data.total >= 13, 'キーワード「餃子」で13品以上');
  check(gyoza.data.items.every(i => i.name.includes('餃子')), '結果は全て名前に餃子を含む');
  const men = await call(page, 'search_menu', { category: '麺類', limit: 100 });
  check(men.data.total === 16 && men.data.items.every(i => i.category === '麺類'), 'カテゴリ絞り込み');
  const cheap = await call(page, 'search_menu', { maxPrice: 400, limit: 100 });
  check(cheap.data.items.every(i => i.price <= 400), '上限価格の絞り込み');
  const kaiou = await call(page, 'search_menu', { query: '海王' });
  check(kaiou.data.items[0] && kaiou.data.items[0].price === 2060, '海王餃子の価格が正しい');
  check(kaiou.data.items[0].priceText === '2,060円', '金額は3桁区切りの表記');
  const none = await call(page, 'search_menu', { query: 'ピザ' });
  check(none.data.total === 0 && none.data.items.length === 0, '無い料理は0件で返す（作り話をしない）');
  const lim = await call(page, 'search_menu', { limit: 3 });
  check(lim.data.items.length === 3 && lim.data.total === 107, '件数上限が効く');
  await page.context().close();
}

console.log('\n[8] list_takeout_items');
{
  const page = await newPage(browser);
  await page.goto(BASE + '/order.html');
  const r = await call(page, 'list_takeout_items');
  check(!r.isError, 'エラーにならない');
  const kaiou = r.data.items.find(i => i.name === '海王餃子セット');
  check(kaiou && kaiou.price === 7760, '海王餃子セットが7,760円（本番実測値）');
  check(kaiou.priceText === '7,760円', '金額は3桁区切りの表記');
  const otsumami = r.data.items.find(i => i.name === 'おつまみ餃子セット');
  check(otsumami && otsumami.priceText === '近日発売', '価格未定の商品は近日発売と答える');
  check(/箱代込み/.test(r.data.shippingNote) && /送料/.test(r.data.shippingNote), '箱代と送料の条件を伝える');
  check(r.data.shopUrl.includes('gyozapekin.official.ec'), 'ネットショップのURLを返す');
  check(r.data.faxOrder && r.data.faxOrder.fax === '072-849-0606', 'FAX注文の案内も返す');
  await page.context().close();
}

console.log('\n[9] 二重登録しても壊れない');
{
  const page = await newPage(browser);
  await page.goto(BASE + '/index.html');
  const n = await page.evaluate(() => {
    const before = window.__registered.length;
    document.dispatchEvent(new Event('DOMContentLoaded'));
    return { before, after: window.__registered.length };
  });
  check(n.before === n.after || n.after === n.before, '登録数が増えない（unregisterしてから登録）');
  check(page.__errors.length === 0, '二重登録でも例外を投げない');
  await page.context().close();
}

console.log('\n[10] 副作用のあるツールを作っていないこと');
{
  const page = await newPage(browser);
  await page.goto(BASE + '/index.html');
  const names = await page.evaluate(() => Object.keys(window.__pekinWebMCPTools));
  const forbidden = names.filter(n => /pay|order_submit|checkout|send|post|delete|login|password|reserve/i.test(n));
  check(forbidden.length === 0, '決済・送信・予約系のツールが存在しない');
  const allReadOnly = await page.evaluate(() =>
    Object.values(window.__pekinWebMCPTools).every(t => t.annotations && t.annotations.readOnlyHint === true));
  check(allReadOnly, '全ツールがreadOnlyHint（Phase 1は読み取り専用）');
  await page.context().close();
}

await browser.close();
server.close();

console.log('\nチェック ' + (pass + fails.length) + '件 / 失敗 ' + fails.length + '件');
if (fails.length) {
  console.log('失敗した項目:');
  fails.forEach(f => console.log('  - ' + f));
  process.exit(1);
}
console.log('すべて合格');
