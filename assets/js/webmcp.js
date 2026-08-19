/*!
 * 海鮮餃子 北京 — WebMCP 対応スクリプト（Phase 1 / 読み取り専用）
 *
 * このファイルは、ブラウザの中にいるAIエージェントに対して
 * 「このサイトでできること」を関数（ツール）として登録します。
 *
 * 設計の約束ごと:
 *   1. 非対応のブラウザでは何もしない。既存のサイトを1バイトも壊さない
 *   2. 仕様が navigator から document へ移動中なので、両対応のラッパーで吸収する
 *   3. 答えは必ず /data/*.json（正本の公開コピー）から取る。HTMLは読まない
 *   4. Phase 1 は読み取り専用。決済・個人情報の送信・SNS投稿は絶対にツール化しない
 *   5. 休みの正本はシフト管理のFirebase。ここで新しいカレンダーを持たない
 *
 * 正本と生成手順: リポジトリの _meta/ を参照
 */
(function () {
  'use strict';

  var DATA = '/data/';
  var VERSION = '1.0.0';

  /* ------------------------------------------------------------------ 基盤 */

  // 仕様が navigator.modelContext から document.modelContext へ移動中のため両対応
  function getModelContext() {
    try {
      if (typeof window === 'undefined') return null;
      if (!window.isSecureContext) return null; // HTTPSのみ
      if (window.top !== window.self) return null; // iframeの中では登録しない
      var doc = (typeof document !== 'undefined' && document.modelContext) || null;
      var nav = (typeof navigator !== 'undefined' && navigator.modelContext) || null;
      return doc || nav || null;
    } catch (e) {
      return null;
    }
  }

  var cache = {};
  function loadJson(name) {
    if (cache[name]) return cache[name];
    cache[name] = fetch(DATA + name + '.json', { credentials: 'omit' })
      .then(function (r) {
        if (!r.ok) throw new Error(name + '.json の取得に失敗しました (' + r.status + ')');
        return r.json();
      })
      .catch(function (e) {
        delete cache[name]; // 次回やり直せるようにする
        throw e;
      });
    return cache[name];
  }

  // MCPの慣習に合わせて {content:[{type:'text',text:...}]} で返す
  function ok(payload) {
    return { content: [{ type: 'text', text: JSON.stringify(payload, null, 2) }] };
  }
  function ng(message) {
    return {
      isError: true,
      content: [{ type: 'text', text: JSON.stringify({ error: String(message) }) }]
    };
  }

  function yen(n) {
    return typeof n === 'number' ? n.toLocaleString('ja-JP') + '円' : null;
  }

  /* -------------------------------------------------------------- 営業日判定 */

  var WD = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  var WD_JA = ['日', '月', '火', '水', '木', '金', '土'];

  // 休みの正本はシフト管理のFirebase。落ちたら静的db.json、それも駄目なら shop.json の既定値
  function loadCalendar(shop) {
    var src = (shop.hours && shop.hours.calendarSource) || {};
    var urls = [src.primary, src.fallback].filter(Boolean);

    function normalize(data) {
      var s = data;
      if (s && typeof s === 'object' && s.pekin_settings) s = s.pekin_settings;
      if (typeof s === 'string') { try { s = JSON.parse(s); } catch (e) { s = {}; } }
      if (!s || typeof s !== 'object') s = {};
      return {
        defaultClosedDays: Array.isArray(s.defaultClosedDays) ? s.defaultClosedDays : null,
        specialDates: (s.specialDates && typeof s.specialDates === 'object') ? s.specialDates : {}
      };
    }

    var chain = Promise.reject();
    urls.forEach(function (u) {
      chain = chain.catch(function () {
        return fetch(u, { credentials: 'omit' }).then(function (r) {
          if (!r.ok) throw new Error('calendar fetch failed');
          return r.json();
        }).then(normalize);
      });
    });

    return chain.catch(function () {
      // 最後の砦: shop.json に書いてある休業曜日
      var closed = (shop.hours.closedDays || []).map(function (d) { return WD.indexOf(d); });
      return { defaultClosedDays: closed, specialDates: {} };
    });
  }

  function pad(n) { return (n < 10 ? '0' : '') + n; }

  function parseDate(input) {
    if (!input) {
      var t = new Date();
      return { y: t.getFullYear(), m: t.getMonth() + 1, d: t.getDate() };
    }
    var m = String(input).match(/^(\d{4})-(\d{1,2})-(\d{1,2})$/);
    if (!m) return null;
    var y = +m[1], mo = +m[2], da = +m[3];
    var chk = new Date(y, mo - 1, da);
    if (chk.getFullYear() !== y || chk.getMonth() !== mo - 1 || chk.getDate() !== da) return null;
    return { y: y, m: mo, d: da };
  }

  /* -------------------------------------------------------------- ツール定義 */

  var TOOLS = {

    get_shop_info: {
      name: 'get_shop_info',
      description:
        '海鮮餃子 北京（大阪府枚方市宮之阪の中華料理店）の基本情報を返します。' +
        '店名・住所・電話番号・営業時間・ラストオーダー・定休日・駐車場・アクセス・支払い方法・' +
        'お持ち帰りや全国発送の可否・公式ページやSNSのURLが含まれます。' +
        '特定の日に営業しているかを知りたいときは check_open_day を使ってください。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, openWorldHint: false },
      execute: function () {
        return loadJson('shop').then(function (s) {
          var a = s.address;
          return ok({
            name: s.name,
            nameEn: s.nameEn,
            description: s.description,
            address: '〒' + a.postalCode + ' ' + a.addressRegion + a.addressLocality + a.streetAddress,
            telephone: s.telephoneDisplay,
            fax: s.faxNumber,
            email: s.email,
            hours: s.hours.open + '〜' + s.hours.close,
            lastOrder: s.hours.lastOrder,
            closedDays: s.hours.closedLabel,
            closedNote: s.hours.closedNote,
            access: s.access,
            parking: s.parking.available
              ? s.parking.spaces + '台（' + s.parking.note + '）' : 'なし',
            payment: s.paymentAccepted,
            takeout: s.features.takeout,
            nationwideShipping: s.features.nationwideShipping,
            onlineReservation: s.features.acceptsReservations,
            reservationNote: s.features.reservationNote,
            englishMenu: s.features.englishMenu,
            links: s.keyPages,
            sameAs: s.sameAs
          });
        }).catch(function (e) { return ng(e.message); });
      }
    },

    check_open_day: {
      name: 'check_open_day',
      description:
        '海鮮餃子 北京が指定した日に営業しているかを判定して返します。' +
        '定休日（火曜日）・不定休（水曜日）・臨時休業・臨時営業をすべて考慮します。' +
        '日付を省略すると今日を判定します。営業時間とラストオーダーも一緒に返します。',
      inputSchema: {
        type: 'object',
        properties: {
          date: {
            type: 'string',
            description: '判定したい日付。YYYY-MM-DD 形式。省略すると今日',
            pattern: '^\\d{4}-\\d{2}-\\d{2}$'
          }
        },
        additionalProperties: false
      },
      annotations: { readOnlyHint: true, openWorldHint: false },
      execute: function (input) {
        var d = parseDate(input && input.date);
        if (!d) return Promise.resolve(ng('日付は YYYY-MM-DD の形式で指定してください'));
        return loadJson('shop').then(function (s) {
          return loadCalendar(s).then(function (cal) {
            var key = d.y + '-' + pad(d.m) + '-' + pad(d.d);
            var dow = new Date(d.y, d.m - 1, d.d).getDay();
            var special = cal.specialDates[key];
            var open, reason;

            if (special) {
              if (special.type === 'open') {
                open = true;
                reason = '臨時営業' + (special.label ? '（' + special.label + '）' : '');
              } else {
                open = false;
                reason = special.label || '臨時休業';
              }
            } else if ((cal.defaultClosedDays || []).indexOf(dow) >= 0) {
              open = false;
              reason = dow === 2 ? '定休日（火曜日）'
                : dow === 3 ? '水曜日は不定休で、現在は休業しています'
                : WD_JA[dow] + '曜日は休業日です';
            } else {
              open = true;
              reason = '通常営業日';
            }

            return ok({
              date: key,
              dayOfWeek: WD_JA[dow] + '曜日',
              isOpen: open,
              reason: reason,
              hours: open ? s.hours.open + '〜' + s.hours.close : null,
              lastOrder: open ? s.hours.lastOrder : null,
              note: '最新のお休みはトップページのカレンダーにも掲載しています',
              telephone: s.telephoneDisplay
            });
          });
        }).catch(function (e) { return ng(e.message); });
      }
    },

    search_menu: {
      name: 'search_menu',
      description:
        '海鮮餃子 北京のお品書きを検索します。餃子・一品料理・天ぷら・麺類・ご飯類・スープ・定食・' +
        'ランチセット・デザート・ドリンクの全107品が対象です。キーワード、カテゴリ、上限価格で絞り込めます。' +
        '価格はすべて税込です。',
      inputSchema: {
        type: 'object',
        properties: {
          query: { type: 'string', description: '料理名に含まれる言葉。例: 餃子、ラーメン、海老' },
          category: { type: 'string', description: 'カテゴリ名。例: 餃子、麺類、定食、ドリンク' },
          maxPrice: { type: 'number', description: 'この金額以下に絞る（税込・円）' },
          limit: { type: 'number', description: '返す件数の上限。既定は20' }
        },
        additionalProperties: false
      },
      annotations: { readOnlyHint: true, openWorldHint: false },
      execute: function (input) {
        input = input || {};
        return loadJson('menu').then(function (m) {
          var q = input.query ? String(input.query).trim() : '';
          var cat = input.category ? String(input.category).trim() : '';
          var max = typeof input.maxPrice === 'number' ? input.maxPrice : null;
          var limit = typeof input.limit === 'number' && input.limit > 0
            ? Math.min(input.limit, 107) : 20;

          var hits = [];
          m.sections.forEach(function (sec) {
            if (cat && sec.section.indexOf(cat) < 0 && cat.indexOf(sec.section) < 0) return;
            sec.items.forEach(function (it) {
              if (q && it.name.indexOf(q) < 0) return;
              if (max !== null && it.price > max) return;
              hits.push({ category: sec.section, name: it.name, price: it.price, priceText: yen(it.price) });
            });
          });

          return ok({
            total: hits.length,
            returned: Math.min(hits.length, limit),
            items: hits.slice(0, limit),
            note: m.note,
            categories: m.sections.map(function (s) { return s.section; }),
            menuUrl: 'https://gyozapekin.com/menu.html'
          });
        }).catch(function (e) { return ng(e.message); });
      }
    },

    list_takeout_items: {
      name: 'list_takeout_items',
      description:
        '海鮮餃子 北京の通販（お取り寄せ・全国発送）で買える冷凍餃子のセットと価格を返します。' +
        '価格は箱代込み・税込で、送料は別です。注文先のネットショップとFAX注文の案内も含みます。',
      inputSchema: { type: 'object', properties: {}, additionalProperties: false },
      annotations: { readOnlyHint: true, openWorldHint: false },
      execute: function () {
        return loadJson('products').then(function (p) {
          return ok({
            items: p.items.map(function (i) {
              return {
                name: i.name,
                price: i.price,
                priceText: i.price ? yen(i.price) : '近日発売',
                contents: i.contents,
                description: i.description,
                availability: i.availability
              };
            }),
            shippingNote: p.shippingNote,
            shopUrl: p.shopUrl,
            orderPageUrl: p.orderPageUrl,
            faxOrder: p.faxOrder
          });
        }).catch(function (e) { return ng(e.message); });
      }
    }
  };

  /* ------------------------------------------------------ ページごとの登録 */

  function detectPage() {
    var p = (location.pathname || '/').toLowerCase();
    if (p === '/' || /\/index\.html$/.test(p)) return 'home';
    if (/\/menu\.html$/.test(p)) return 'menu';
    if (/\/order\.html$/.test(p)) return 'order';
    if (/\/about\.html$/.test(p)) return 'about';
    return 'other';
  }

  function toolsForPage(page) {
    // どのページでも店の基本情報と営業日は答えられるようにする
    var list = ['get_shop_info', 'check_open_day'];
    if (page === 'home' || page === 'menu') list.push('search_menu');
    if (page === 'home' || page === 'order') list.push('list_takeout_items');
    return list.map(function (n) { return TOOLS[n]; });
  }

  function register(mc, tools) {
    // まとめて差し替えられるAPIがあればそちらを使う
    if (typeof mc.provideContext === 'function') {
      mc.provideContext({ tools: tools });
      return tools.length;
    }
    if (typeof mc.registerTool !== 'function') return 0;
    var n = 0;
    tools.forEach(function (t) {
      try {
        if (typeof mc.unregisterTool === 'function') {
          try { mc.unregisterTool(t.name); } catch (e) { /* 未登録なら無視 */ }
        }
        mc.registerTool(t);
        n++;
      } catch (e) {
        if (window.console && console.warn) console.warn('[WebMCP] 登録に失敗:', t.name, e);
      }
    });
    return n;
  }

  function init() {
    var mc = getModelContext();
    if (!mc) return; // 非対応ブラウザ・非HTTPS・iframe内では何もしない
    var page = detectPage();
    var count = register(mc, toolsForPage(page));
    window.__pekinWebMCP = { version: VERSION, page: page, registered: count };
  }

  // テストから直接叩けるように、ツール定義も公開しておく
  window.__pekinWebMCPTools = TOOLS;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
