const NEWS = [
  {
    date: "2026.01.09",
    category: "MUSIC",
    member: null,
    title: "シングル「愛憎」リリース",
    body: "呪術廻戦 死滅回游編 オープニングテーマ。"
  },
  {
    date: "2025.12.28",
    category: "LIVE",
    member: null,
    title: "東京ドーム5DAYS 全公演終了",
    body: "5公演・約25万人を動員。全公演ソールドアウト。"
  },
  {
    date: "2025.09.01",
    category: "MUSIC",
    member: null,
    title: "「So Bad」リリース",
    body: "USJハロウィンホラーナイト2025 公式テーマ曲。"
  },
  {
    date: "2025.03.01",
    category: "MUSIC",
    member: null,
    title: "「Twilight!!!」リリース",
    body: "劇場版名探偵コナン 隻眼の残像 エンディングテーマ。"
  },
  {
    date: "2024.12.14",
    category: "LIVE",
    member: null,
    title: "東京ドームツアー開幕",
    body: "12/14より東京ドーム5公演がスタート。"
  },
  {
    date: "2024.03.01",
    category: "MUSIC",
    member: null,
    title: "「逆夢」進撃の巨人 The Final Season Part3 ED",
    body: "進撃の巨人最終章エンディングテーマとして配信開始。"
  },
  {
    date: "2023.10.06",
    category: "MUSIC",
    member: null,
    title: "「Specialz」リリース",
    body: "呪術廻戦 渋谷事変 オープニングテーマ。国際的に大きな反響。"
  },
  {
    date: "2023.07.15",
    category: "LIVE",
    member: null,
    title: "スタジアムツアー2023 開幕",
    body: "味の素スタジアムを皮切りにスタジアムツアー開幕。"
  },
  {
    date: "2022.11.16",
    category: "MUSIC",
    member: null,
    title: "4thアルバム「THE GREATEST UNKNOWN」リリース",
    body: "オリコン週間アルバムランキング1位を獲得。"
  },
  {
    date: "2022.01.12",
    category: "MUSIC",
    member: null,
    title: "「逆夢」リリース",
    body: "進撃の巨人 The Final Season Part2 エンディングテーマ。"
  },
  // 常田大希
  {
    date: "2021.07.16",
    category: "SOLO",
    member: "tsuneta",
    title: "映画「竜とそばかすの姫」音楽担当",
    body: "millennium parade名義で細田守監督作品の楽曲・劇伴を担当。"
  },
  {
    date: "2023.10.06",
    category: "MUSIC",
    member: "tsuneta",
    title: "「Specialz」作詞・作曲・プロデュース",
    body: "呪術廻戦タイアップ曲を手がけ、国際的な注目を集める。"
  },
  // 井口理
  {
    date: "2024.04.01",
    category: "ACTOR",
    member: "iguchi",
    title: "ドラマ「燕は戻ってこない」出演",
    body: "NHKドラマに出演。演技力が高く評価される。"
  },
  {
    date: "2023.01.08",
    category: "ACTOR",
    member: "iguchi",
    title: "NHK大河ドラマ「どうする家康」出演",
    body: "大河ドラマに出演。音楽と俳優の二刀流を継続。"
  },
  {
    date: "2021.04.13",
    category: "ACTOR",
    member: "iguchi",
    title: "ドラマ「大豆田とわ子と三人の元夫」出演",
    body: "フジテレビ系ドラマに出演。演技が大きな話題に。"
  },
  // 新井和輝
  {
    date: "2022.11.16",
    category: "MUSIC",
    member: "arai",
    title: "「THE GREATEST UNKNOWN」参加",
    body: "複雑なアレンジの中でもグルーヴを失わないベースラインが評価。"
  },
  // 勢喜遊
  {
    date: "2022.11.16",
    category: "MUSIC",
    member: "seki",
    title: "「THE GREATEST UNKNOWN」参加",
    body: "多彩なリズムアプローチでバンドの新境地を開拓。"
  }
];

/**
 * ニュースアイテムのHTMLを生成して指定要素に挿入する
 * @param {string} containerId - 挿入先要素のid
 * @param {Object} options - { member: string|null, limit: number }
 */
function renderNews(containerId, options = {}) {
  const { member = null, limit = 5 } = options;
  const container = document.getElementById(containerId);
  if (!container) return;

  const filtered = NEWS
    .filter(n => member === null ? true : n.member === member)
    .slice(0, limit);

  if (filtered.length === 0) {
    container.innerHTML = '<p style="font-size:12px;color:#888;">ニュースはありません。</p>';
    return;
  }

  const categoryColors = {
    MUSIC: { bg: '#111', color: '#fff' },
    LIVE:  { bg: '#e63329', color: '#fff' },
    SOLO:  { bg: '#2255cc', color: '#fff' },
    ACTOR: { bg: '#119944', color: '#fff' },
    OTHER: { bg: '#888', color: '#fff' }
  };

  container.innerHTML = filtered.map(n => {
    const c = categoryColors[n.category] || categoryColors.OTHER;
    return `
      <div class="news-item">
        <div class="news-date">${n.date}</div>
        <div class="news-badge" style="background:${c.bg};color:${c.color}">${n.category}</div>
        <div class="news-text"><strong>${escHtmlNews(n.title)}</strong> — ${escHtmlNews(n.body)}</div>
      </div>`;
  }).join('');
}

function escHtmlNews(str) {
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

/**
 * 検索 + ページネーション付きニュース表示（メンバーページ用）
 * @param {string} containerId
 * @param {Object} options - { member: string, pageSize: number }
 */
function renderNewsInteractive(containerId, options = {}) {
  const { member = null, pageSize = 5 } = options;
  const root = document.getElementById(containerId);
  if (!root) return;

  const categoryColors = {
    MUSIC: { bg: '#111',    color: '#fff' },
    LIVE:  { bg: '#e63329', color: '#fff' },
    SOLO:  { bg: '#2255cc', color: '#fff' },
    ACTOR: { bg: '#119944', color: '#fff' },
    OTHER: { bg: '#888',    color: '#fff' }
  };

  const base = member ? NEWS.filter(n => n.member === member) : NEWS;

  let query = '';
  let page  = 1;

  function filtered() {
    if (!query) return base;
    const q = query.toLowerCase();
    return base.filter(n =>
      n.title.toLowerCase().includes(q) ||
      n.body.toLowerCase().includes(q) ||
      n.category.toLowerCase().includes(q)
    );
  }

  function draw() {
    const items = filtered();
    const total = items.length;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    if (page > totalPages) page = totalPages;
    const slice = items.slice((page - 1) * pageSize, page * pageSize);

    const listHtml = slice.length === 0
      ? '<p style="font-size:12px;color:#888;padding:8px 0;">該当するニュースはありません。</p>'
      : slice.map(n => {
          const c = categoryColors[n.category] || categoryColors.OTHER;
          return `<div class="news-item">
            <div class="news-date">${escHtmlNews(n.date)}</div>
            <div class="news-badge" style="background:${c.bg};color:${c.color}">${n.category}</div>
            <div class="news-text"><strong>${escHtmlNews(n.title)}</strong> — ${escHtmlNews(n.body)}</div>
          </div>`;
        }).join('');

    const pageButtons = [];
    for (let i = 1; i <= totalPages; i++) {
      pageButtons.push(
        `<button class="ni-page-btn${i === page ? ' ni-page-active' : ''}" data-p="${i}">${i}</button>`
      );
    }

    root.innerHTML = `
      <div class="ni-search-wrap">
        <input class="ni-search" type="text" placeholder="キーワードで絞り込む…" value="${escHtmlNews(query)}">
        <span class="ni-count">${total} 件</span>
      </div>
      <div class="ni-list">${listHtml}</div>
      ${totalPages > 1 ? `<div class="ni-pagination">${pageButtons.join('')}</div>` : ''}
    `;

    root.querySelector('.ni-search').addEventListener('input', e => {
      query = e.target.value;
      page  = 1;
      draw();
      root.querySelector('.ni-search').focus();
    });

    root.querySelectorAll('.ni-page-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        page = Number(btn.dataset.p);
        draw();
      });
    });
  }

  const style = document.getElementById('_ni_style');
  if (!style) {
    const s = document.createElement('style');
    s.id = '_ni_style';
    s.textContent = `
      .ni-search-wrap { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
      .ni-search { width:150px; font-family:'IBM Plex Mono',monospace; font-size:10px; padding:3px 8px; border:1px solid #ddd; background:#fff; outline:none; }
      .ni-search:focus { border-color:#111; }
      .ni-count { font-family:'IBM Plex Mono',monospace; font-size:10px; color:#aaa; white-space:nowrap; }
      .ni-list { display:flex; flex-direction:column; }
      .news-item { display:flex; align-items:baseline; gap:10px; padding:9px 0; border-bottom:1px solid #eee; font-size:12px; }
      .news-item:last-child { border-bottom:none; }
      .news-date { font-family:'IBM Plex Mono',monospace; font-size:10px; color:#888; white-space:nowrap; }
      .news-badge { font-family:'IBM Plex Mono',monospace; font-size:9px; font-weight:700; padding:1px 6px; white-space:nowrap; }
      .news-text { color:#333; line-height:1.6; }
      .ni-pagination { display:flex; gap:4px; margin-top:10px; }
      .ni-page-btn { font-family:'IBM Plex Mono',monospace; font-size:10px; font-weight:700; padding:3px 9px; border:1px solid #ddd; background:#fff; cursor:pointer; transition:background .12s,color .12s; }
      .ni-page-btn:hover { border-color:#111; }
      .ni-page-btn.ni-page-active { background:#111; color:#fff; border-color:#111; }
    `;
    document.head.appendChild(s);
  }

  draw();
}
