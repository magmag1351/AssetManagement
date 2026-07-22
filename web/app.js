/* ==========================================================================
   AssetPlanner - Frontend Application Logic (Multi-Profile & Multi-Account System)
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();

  const state = {
    currentView: "dashboard",
    selectedMonth: "all",
    selectedAccount: "all",
    summaryData: null,
    transactions: [],
    rules: { prefix_rules: {}, keyword_rules: {}, default_genre: "未分類" },
    profilesConfig: { active_profile_id: "profile_default", profiles: [] },
    editingTransaction: null,
    charts: {
      trends: null,
      genre: null,
      card: null,
      paymentMethod: null
    }
  };

  const elements = {
    navItems: document.querySelectorAll(".nav-item"),
    views: document.querySelectorAll(".view-section"),
    pageTitle: document.getElementById("page-title"),
    breadcrumbCurrent: document.getElementById("breadcrumb-current"),
    globalMonthSelect: document.getElementById("global-month-select"),
    globalAccountSelect: document.getElementById("global-account-select"),
    btnQuickImport: document.getElementById("btn-quick-import"),
    btnCmdSearch: document.getElementById("btn-cmd-search"),

    // プロファイル要素
    userProfileTrigger: document.getElementById("user-profile-trigger"),
    sidebarAvatar: document.getElementById("sidebar-avatar"),
    sidebarUserName: document.getElementById("sidebar-user-name"),
    sidebarAccountTag: document.getElementById("sidebar-account-tag"),
    profileModal: document.getElementById("profile-modal"),
    profileSelectionList: document.getElementById("profile-selection-list"),
    btnCloseProfileModal: document.getElementById("btn-close-profile-modal"),
    newProfileName: document.getElementById("new-profile-name"),
    newProfileAccount: document.getElementById("new-profile-account"),
    newProfileAvatar: document.getElementById("new-profile-avatar"),
    btnAddProfile: document.getElementById("btn-add-profile"),

    // 口座管理要素
    editProfileAccountsList: document.getElementById("edit-profile-accounts-list"),
    newAccountNameInput: document.getElementById("new-account-name-input"),
    btnAddAccountToProfile: document.getElementById("btn-add-account-to-profile"),

    // カスタム確認モーダル要素
    customConfirmModal: document.getElementById("custom-confirm-modal"),
    confirmModalTitle: document.getElementById("confirm-modal-title"),
    confirmModalMessage: document.getElementById("confirm-modal-message"),
    btnConfirmCancel: document.getElementById("btn-confirm-cancel"),
    btnConfirmOk: document.getElementById("btn-confirm-ok"),
    btnCloseConfirmModal: document.getElementById("btn-close-confirm-modal"),

    // KPI
    kpiNetBalance: document.getElementById("kpi-net-balance"),
    kpiBalanceStatus: document.getElementById("kpi-balance-status"),
    kpiTrendChip: document.getElementById("kpi-trend-chip"),
    kpiTotalIncome: document.getElementById("kpi-total-income"),
    kpiTotalExpense: document.getElementById("kpi-total-expense"),
    kpiTotalTransfers: document.getElementById("kpi-total-transfers"),

    // カテゴリゲージ & レジェンド
    genreLegendList: document.getElementById("genre-legend-list"),
    categoryGaugesList: document.getElementById("category-gauges-list"),

    // テーブル
    dashboardRecentTable: document.getElementById("dashboard-recent-table"),
    fullTransactionsTable: document.getElementById("full-transactions-table"),
    txSearchInput: document.getElementById("tx-search-input"),
    txGenreFilter: document.getElementById("tx-genre-filter"),
    txCountBadge: document.getElementById("tx-count-badge"),

    // インポート
    btnStartImport: document.getElementById("btn-start-import"),
    importLogConsole: document.getElementById("import-log-console"),

    // ルール
    prefixRulesList: document.getElementById("prefix-rules-list"),
    keywordRulesList: document.getElementById("keyword-rules-list"),
    btnAddPrefixRule: document.getElementById("btn-add-prefix-rule"),
    btnAddKeywordRule: document.getElementById("btn-add-keyword-rule"),
    btnSaveRules: document.getElementById("btn-save-rules"),

    // ジャンル編集モーダル
    genreModal: document.getElementById("genre-modal"),
    modalTxDesc: document.getElementById("modal-tx-desc"),
    modalGenreInput: document.getElementById("modal-genre-input"),
    btnCloseModal: document.getElementById("btn-close-modal"),
    btnCancelModal: document.getElementById("btn-cancel-modal"),
    btnConfirmModal: document.getElementById("btn-confirm-modal")
  };

  // --- Toast 通知機能 ---
  function showToast(message, type = "success") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      <i data-lucide="${type === 'success' ? 'check-circle-2' : 'alert-circle'}"></i>
      <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);
    lucide.createIcons();

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(20px)";
      toast.style.transition = "all 0.3s ease";
      setTimeout(() => toast.remove(), 300);
    }, 3200);
  }

  // --- インアプリ確認モーダル機能 ---
  let pendingConfirmAction = null;

  function showCustomConfirm(title, message, onConfirm) {
    if (!elements.customConfirmModal) return;

    elements.confirmModalTitle.textContent = title;
    elements.confirmModalMessage.textContent = message;
    pendingConfirmAction = onConfirm;

    elements.customConfirmModal.classList.add("active");
  }

  function closeCustomConfirm() {
    if (elements.customConfirmModal) elements.customConfirmModal.classList.remove("active");
    pendingConfirmAction = null;
  }

  if (elements.btnConfirmCancel) elements.btnConfirmCancel.addEventListener("click", closeCustomConfirm);
  if (elements.btnCloseConfirmModal) elements.btnCloseConfirmModal.addEventListener("click", closeCustomConfirm);
  if (elements.btnConfirmOk) {
    elements.btnConfirmOk.addEventListener("click", async () => {
      if (pendingConfirmAction) {
        const action = pendingConfirmAction;
        closeCustomConfirm();
        await action();
      }
    });
  }

  const viewTitles = {
    dashboard: "ダッシュボード",
    transactions: "取引明細一覧",
    import: "明細インポート",
    rules: "ジャンル分類設定"
  };

  window.switchView = (viewName) => {
    state.currentView = viewName;
    elements.navItems.forEach(item => {
      item.classList.toggle("active", item.dataset.view === viewName);
    });
    elements.views.forEach(view => {
      view.classList.toggle("active", view.id === `view-${viewName}`);
    });
    if (viewTitles[viewName]) {
      elements.pageTitle.textContent = viewTitles[viewName];
      elements.breadcrumbCurrent.textContent = viewTitles[viewName];
    }
  };

  elements.navItems.forEach(item => {
    item.addEventListener("click", () => switchView(item.dataset.view));
  });

  // Cmd+K Shortcut
  window.addEventListener("keydown", (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
      e.preventDefault();
      switchView("transactions");
      elements.txSearchInput.focus();
    }
  });

  if (elements.btnCmdSearch) {
    elements.btnCmdSearch.addEventListener("click", () => {
      switchView("transactions");
      elements.txSearchInput.focus();
    });
  }

  // --- プロファイル API & UI 通信 ---
  async function fetchProfiles() {
    try {
      const res = await fetch("/api/profiles");
      state.profilesConfig = await res.json();
      updateSidebarProfileCard();
      renderProfileSelectionList();
      updateAccountSelector();
    } catch (err) {
      console.error("Profiles fetch error:", err);
    }
  }

  function updateSidebarProfileCard() {
    const activeId = state.profilesConfig.active_profile_id;
    const activeProfile = state.profilesConfig.profiles.find(p => p.id === activeId) || state.profilesConfig.profiles[0];
    if (activeProfile) {
      elements.sidebarUserName.textContent = activeProfile.name;
      elements.sidebarAccountTag.textContent = activeProfile.account_info || "口座連携";
      elements.sidebarAvatar.textContent = activeProfile.avatar;
      elements.sidebarAvatar.style.background = activeProfile.color ? `linear-gradient(135deg, ${activeProfile.color}, #059669)` : '';
    }
  }

  function updateAccountSelector() {
    if (!elements.globalAccountSelect) return;
    const activeId = state.profilesConfig.active_profile_id;
    const activeProfile = state.profilesConfig.profiles.find(p => p.id === activeId) || state.profilesConfig.profiles[0];

    const currentVal = elements.globalAccountSelect.value || "all";
    elements.globalAccountSelect.innerHTML = '<option value="all">すべての口座・カード (全統括)</option>';

    if (activeProfile && activeProfile.accounts) {
      activeProfile.accounts.forEach(acc => {
        const opt = document.createElement("option");
        opt.value = acc.name;
        opt.textContent = `${acc.type === 'CARD' ? '💳' : '🏦'} ${acc.name}`;
        elements.globalAccountSelect.appendChild(opt);
      });
    }

    elements.globalAccountSelect.value = currentVal;
  }

  if (elements.globalAccountSelect) {
    elements.globalAccountSelect.addEventListener("change", (e) => {
      state.selectedAccount = e.target.value;
      fetchSummary();
      fetchTransactions();
    });
  }

  function renderProfileSelectionList() {
    const activeId = state.profilesConfig.active_profile_id;
    elements.profileSelectionList.innerHTML = state.profilesConfig.profiles.map(p => {
      const isActive = p.id === activeId;
      const isDefault = p.id === "profile_default";
      const accCount = (p.accounts || []).length;
      return `
        <div class="profile-item-row ${isActive ? 'active' : ''}" onclick="switchProfile('${p.id}')">
          <div class="profile-avatar" style="background-color: ${p.color || '#6366f1'}">${escapeHtml(p.avatar)}</div>
          <div class="profile-details">
            <span class="profile-name">${escapeHtml(p.name)} (${accCount}口座)</span>
            <span class="profile-account">${escapeHtml(p.account_info || '口座連携')}</span>
          </div>
          ${isActive ? '<i data-lucide="check" class="active-check"></i>' : ''}
          <button class="btn-icon-edit ml-2" onclick="startEditProfile(event, '${p.id}')" title="プロファイルを編集"><i data-lucide="pencil"></i></button>
          ${!isDefault ? `<button class="btn-icon-danger ml-1" onclick="deleteProfile(event, '${p.id}', '${escapeJsString(p.name)}')" title="プロファイルを削除"><i data-lucide="trash-2"></i></button>` : ''}
        </div>
      `;
    }).join("");
    lucide.createIcons();
  }

  window.startEditProfile = (event, profileId) => {
    event.stopPropagation();
    const profile = state.profilesConfig.profiles.find(p => p.id === profileId);
    if (!profile) return;

    const addSec = document.getElementById("profile-add-section");
    const editSec = document.getElementById("profile-edit-section");

    if (addSec && editSec) {
      addSec.style.display = "none";
      editSec.style.display = "block";
    }

    document.getElementById("edit-profile-id").value = profile.id;
    document.getElementById("edit-profile-name").value = profile.name;
    document.getElementById("edit-profile-account").value = profile.account_info || "";
    document.getElementById("edit-profile-avatar").value = profile.avatar;

    renderEditProfileAccountsList(profile);
  };

  function renderEditProfileAccountsList(profile) {
    if (!elements.editProfileAccountsList) return;
    const accounts = profile.accounts || [];

    if (accounts.length === 0) {
      elements.editProfileAccountsList.innerHTML = `<span class="text-muted text-xs">登録されている口座・カードがありません。</span>`;
      return;
    }

    elements.editProfileAccountsList.innerHTML = accounts.map(acc => `
      <span class="account-pill">
        <span>${acc.type === 'CARD' ? '💳' : '🏦'} ${escapeHtml(acc.name)}</span>
        <button class="btn-remove-acc" onclick="deleteAccountFromProfile(event, '${profile.id}', '${acc.id}')" title="口座を削除"><i data-lucide="x"></i></button>
      </span>
    `).join("");
    lucide.createIcons();
  }

  window.deleteAccountFromProfile = async (event, profileId, accountId) => {
    event.stopPropagation();
    try {
      const res = await fetch("/api/profiles/accounts/delete", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profileId, account_id: accountId })
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast(data.message || "口座を削除しました。");
        await fetchProfiles();
        const updatedProf = state.profilesConfig.profiles.find(p => p.id === profileId);
        if (updatedProf) renderEditProfileAccountsList(updatedProf);
      }
    } catch (err) {
      showToast("口座削除エラー: " + err, "error");
    }
  };

  if (elements.btnAddAccountToProfile) {
    elements.btnAddAccountToProfile.addEventListener("click", async () => {
      const profileId = document.getElementById("edit-profile-id").value;
      const accountName = elements.newAccountNameInput.value.trim();

      if (!accountName) {
        showToast("口座・カード名を入力してください。", "error");
        return;
      }

      try {
        const res = await fetch("/api/profiles/accounts/add", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            profile_id: profileId,
            name: accountName,
            type: accountName.toLowerCase().includes("card") || accountName.includes("カード") || accountName.includes("マスター") ? "CARD" : "BANK"
          })
        });
        const data = await res.json();
        if (data.status === "success") {
          showToast(data.message || "口座を追加しました。");
          elements.newAccountNameInput.value = "";
          await fetchProfiles();
          const updatedProf = state.profilesConfig.profiles.find(p => p.id === profileId);
          if (updatedProf) renderEditProfileAccountsList(updatedProf);
        } else {
          showToast(data.error || "口座追加に失敗しました。", "error");
        }
      } catch (err) {
        showToast("口座追加エラー: " + err, "error");
      }
    });
  }

  function cancelEditProfile() {
    const addSec = document.getElementById("profile-add-section");
    const editSec = document.getElementById("profile-edit-section");

    if (addSec && editSec) {
      editSec.style.display = "none";
      addSec.style.display = "block";
    }
  }

  document.getElementById("btn-cancel-edit-profile")?.addEventListener("click", cancelEditProfile);

  document.getElementById("btn-save-edit-profile")?.addEventListener("click", async () => {
    const profileId = document.getElementById("edit-profile-id").value;
    const name = document.getElementById("edit-profile-name").value.trim();
    const account = document.getElementById("edit-profile-account").value.trim();
    const avatar = document.getElementById("edit-profile-avatar").value.trim();

    if (!name) {
      showToast("プロファイル名を入力してください。", "error");
      return;
    }

    try {
      const res = await fetch("/api/profiles/edit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          profile_id: profileId,
          name: name,
          account_info: account,
          avatar: avatar
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast(data.message || "プロファイルを更新しました。");
        cancelEditProfile();
        await fetchProfiles();
        await fetchSummary();
        await fetchTransactions();
      } else {
        showToast(data.error || "更新に失敗しました。", "error");
      }
    } catch (err) {
      showToast("プロファイル更新エラー: " + err, "error");
    }
  });

  window.switchProfile = async (profileId) => {
    try {
      const res = await fetch("/api/profiles/switch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ profile_id: profileId })
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast("プロファイルを切り替えました。");
        state.selectedAccount = "all";
        await fetchProfiles();
        await fetchSummary();
        await fetchTransactions();
      }
    } catch (err) {
      showToast("プロファイル切り替えエラー: " + err, "error");
    }
  };

  window.deleteProfile = (event, profileId, profileName) => {
    event.stopPropagation();
    showCustomConfirm(
      "プロファイルの削除確認",
      `プロファイル『${profileName}』を削除してもよろしいですか？ 紐づく取引データも削除されます。`,
      async () => {
        try {
          const res = await fetch("/api/profiles/delete", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ profile_id: profileId })
          });
          const data = await res.json();
          if (data.status === "success") {
            showToast(`プロファイル『${profileName}』を削除しました。`);
            await fetchProfiles();
            await fetchSummary();
            await fetchTransactions();
          } else {
            showToast(data.error || "削除できませんでした。", "error");
          }
        } catch (err) {
          showToast("プロファイル削除エラー: " + err, "error");
        }
      }
    );
  };

  elements.userProfileTrigger.addEventListener("click", () => {
    elements.profileModal.classList.add("active");
  });

  elements.btnCloseProfileModal.addEventListener("click", () => {
    elements.profileModal.classList.remove("active");
  });

  elements.btnAddProfile.addEventListener("click", async () => {
    const name = elements.newProfileName.value.trim();
    const account = elements.newProfileAccount.value.trim() || "メイン口座";
    const avatar = elements.newProfileAvatar.value.trim() || name.substring(0, 2);

    if (!name) {
      showToast("プロファイル名を入力してください。", "error");
      return;
    }

    try {
      const res = await fetch("/api/profiles/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name,
          account_info: account,
          avatar: avatar,
          color: "#6366f1"
        })
      });
      const data = await res.json();
      if (data.status === "success") {
        showToast(data.message || "新規プロファイルを作成しました。");
        elements.newProfileName.value = "";
        elements.newProfileAccount.value = "";
        elements.newProfileAvatar.value = "";
        await fetchProfiles();
        await fetchSummary();
        await fetchTransactions();
      } else {
        showToast(data.error || "作成に失敗しました。", "error");
      }
    } catch (err) {
      showToast("プロファイル作成エラー: " + err, "error");
    }
  });

  // --- API データ取得 ---
  async function fetchSummary() {
    try {
      let url = `/api/summary?account=${encodeURIComponent(state.selectedAccount)}`;
      const res = await fetch(url);
      state.summaryData = await res.json();
      updateMonthSelector();
      renderKPIs();
      renderCharts();
      renderCategoryGauges();
      renderDashboardRecentTable();
    } catch (err) {
      console.error("Summary fetch error:", err);
    }
  }

  async function fetchTransactions() {
    try {
      let url = `/api/transactions?account=${encodeURIComponent(state.selectedAccount)}&`;
      if (state.selectedMonth !== "all") url += `month=${state.selectedMonth}&`;
      const res = await fetch(url);
      const data = await res.json();
      state.transactions = data.transactions;
      renderGenreFilterOptions();
      renderTransactionsTable();
    } catch (err) {
      console.error("Transactions fetch error:", err);
    }
  }

  async function fetchRules() {
    try {
      const res = await fetch("/api/rules");
      state.rules = await res.json();
      renderRulesEditor();
    } catch (err) {
      console.error("Rules fetch error:", err);
    }
  }

  function updateMonthSelector() {
    if (!state.summaryData) return;
    const currentVal = elements.globalMonthSelect.value;
    elements.globalMonthSelect.innerHTML = '<option value="all">全期間 (累計)</option>';
    state.summaryData.months.forEach(month => {
      const opt = document.createElement("option");
      opt.value = month;
      opt.textContent = month;
      elements.globalMonthSelect.appendChild(opt);
    });
    elements.globalMonthSelect.value = currentVal;
  }

  elements.globalMonthSelect.addEventListener("change", (e) => {
    state.selectedMonth = e.target.value;
    renderKPIs();
    renderCharts();
    renderCategoryGauges();
    fetchTransactions();
  });

  // --- KPI ---
  function renderKPIs() {
    if (!state.summaryData) return;

    let income = 0, expense = 0, transfers = 0;

    if (state.selectedMonth === "all") {
      income = state.summaryData.kpis.total_income;
      expense = state.summaryData.kpis.total_expense;
      transfers = state.summaryData.kpis.total_transfers;
    } else {
      const m = state.summaryData.monthly_summary[state.selectedMonth];
      if (m) {
        income = m.income;
        expense = m.expense;
        transfers = m.internal_transfer;
      }
    }

    const balance = income - expense;
    elements.kpiNetBalance.textContent = `¥${balance.toLocaleString()}`;
    elements.kpiTotalIncome.textContent = `¥${income.toLocaleString()}`;
    elements.kpiTotalExpense.textContent = `¥${expense.toLocaleString()}`;
    elements.kpiTotalTransfers.textContent = `¥${transfers.toLocaleString()}`;

    if (balance >= 0) {
      elements.kpiNetBalance.className = "kpi-value positive";
      elements.kpiBalanceStatus.textContent = "黒字 (資産増加傾向)";
      elements.kpiTrendChip.textContent = "▲ 健全";
      elements.kpiTrendChip.className = "trend-chip positive";
    } else {
      elements.kpiNetBalance.className = "kpi-value negative";
      elements.kpiBalanceStatus.textContent = "赤字 (支出超過)";
      elements.kpiTrendChip.textContent = "▼ 超過";
      elements.kpiTrendChip.className = "trend-chip negative";
    }
  }

  // --- グラフ描画 ---
  function renderCharts() {
    if (!state.summaryData) return;

    const months = state.summaryData.months;
    const monthlySummary = state.summaryData.monthly_summary;
    const incomeData = months.map(m => monthlySummary[m].income);
    const expenseData = months.map(m => monthlySummary[m].expense);

    const ctxTrends = document.getElementById("chart-monthly-trends").getContext("2d");
    if (state.charts.trends) state.charts.trends.destroy();

    const gradIncome = ctxTrends.createLinearGradient(0, 0, 0, 260);
    gradIncome.addColorStop(0, "rgba(16, 185, 129, 0.4)");
    gradIncome.addColorStop(1, "rgba(16, 185, 129, 0.0)");

    const gradExpense = ctxTrends.createLinearGradient(0, 0, 0, 260);
    gradExpense.addColorStop(0, "rgba(244, 63, 94, 0.4)");
    gradExpense.addColorStop(1, "rgba(244, 63, 94, 0.0)");

    state.charts.trends = new Chart(ctxTrends, {
      type: "line",
      data: {
        labels: months,
        datasets: [
          {
            label: "収入",
            data: incomeData,
            borderColor: "#10b981",
            backgroundColor: gradIncome,
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointRadius: 4,
            pointBackgroundColor: "#10b981"
          },
          {
            label: "支出",
            data: expenseData,
            borderColor: "#f43f5e",
            backgroundColor: gradExpense,
            borderWidth: 3,
            fill: true,
            tension: 0.35,
            pointRadius: 4,
            pointBackgroundColor: "#f43f5e"
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { labels: { color: "#a1a1aa", font: { family: "Plus Jakarta Sans", size: 12 } } }
        },
        scales: {
          x: { ticks: { color: "#71717a" }, grid: { color: "rgba(255,255,255,0.04)" } },
          y: { ticks: { color: "#71717a" }, grid: { color: "rgba(255,255,255,0.04)" } }
        }
      }
    });

    let genreMap = {};
    let cardMap = {};
    let paymentMethodMap = {};

    if (state.selectedMonth === "all") {
      months.forEach(m => {
        const bg = monthlySummary[m].by_genre || {};
        const bc = monthlySummary[m].by_card || {};
        const bpm = monthlySummary[m].by_payment_method || {};

        for (const [k, v] of Object.entries(bg)) genreMap[k] = (genreMap[k] || 0) + v;
        for (const [k, v] of Object.entries(bc)) cardMap[k] = (cardMap[k] || 0) + v;
        for (const [k, v] of Object.entries(bpm)) paymentMethodMap[k] = (paymentMethodMap[k] || 0) + v;
      });
    } else {
      const m = monthlySummary[state.selectedMonth];
      if (m) {
        genreMap = m.by_genre || {};
        cardMap = m.by_card || {};
        paymentMethodMap = m.by_payment_method || {};
      }
    }

    const palette = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#38bdf8", "#8b5cf6", "#14b8a6", "#f97316"];

    // ジャンル別 Doughnut
    const sortedGenres = Object.entries(genreMap).sort((a, b) => b[1] - a[1]);
    const totalGenreExp = sortedGenres.reduce((acc, curr) => acc + curr[1], 0);

    const genreLabels = sortedGenres.map(x => x[0]);
    const genreValues = sortedGenres.map(x => x[1]);

    const ctxGenre = document.getElementById("chart-genre-breakdown").getContext("2d");
    if (state.charts.genre) state.charts.genre.destroy();

    state.charts.genre = new Chart(ctxGenre, {
      type: "doughnut",
      data: {
        labels: genreLabels,
        datasets: [{
          data: genreValues,
          backgroundColor: palette,
          borderWidth: 0,
          hoverOffset: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } }
      }
    });

    if (elements.genreLegendList) {
      elements.genreLegendList.innerHTML = sortedGenres.slice(0, 5).map(([name, amount], idx) => {
        const pct = totalGenreExp > 0 ? ((amount / totalGenreExp) * 100).toFixed(1) : 0;
        const color = palette[idx % palette.length];
        return `
          <div class="legend-item">
            <div class="legend-dot-label">
              <span class="legend-dot" style="background-color: ${color}"></span>
              <span>${escapeHtml(name)} (${pct}%)</span>
            </div>
            <span class="legend-val">¥${amount.toLocaleString()}</span>
          </div>
        `;
      }).join("");
    }

    // 決済手段別 Doughnut
    const pmLabels = Object.keys(paymentMethodMap);
    const pmValues = Object.values(paymentMethodMap);
    const ctxPayment = document.getElementById("chart-payment-method-breakdown")?.getContext("2d");
    if (ctxPayment) {
      if (state.charts.paymentMethod) state.charts.paymentMethod.destroy();
      state.charts.paymentMethod = new Chart(ctxPayment, {
        type: "doughnut",
        data: {
          labels: pmLabels,
          datasets: [{
            data: pmValues,
            backgroundColor: ["#6366f1", "#10b981"],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "right", labels: { color: "#a1a1aa", font: { size: 11 } } } }
        }
      });
    }

    // クレジットカード別 Doughnut
    const cardLabels = Object.keys(cardMap);
    const cardValues = Object.values(cardMap);
    const ctxCard = document.getElementById("chart-card-breakdown")?.getContext("2d");
    if (ctxCard) {
      if (state.charts.card) state.charts.card.destroy();
      state.charts.card = new Chart(ctxCard, {
        type: "doughnut",
        data: {
          labels: cardLabels,
          datasets: [{
            data: cardValues,
            backgroundColor: ["#38bdf8", "#fbbf24", "#34d399", "#f472b6", "#a855f7"],
            borderWidth: 0
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: "right", labels: { color: "#a1a1aa", font: { size: 12 } } } }
        }
      });
    }
  }

  // --- カテゴリ別 支出ゲージ ---
  function renderCategoryGauges() {
    if (!state.summaryData || !elements.categoryGaugesList) return;

    let genreMap = {};
    const months = state.summaryData.months;
    const monthlySummary = state.summaryData.monthly_summary;

    if (state.selectedMonth === "all") {
      months.forEach(m => {
        const bg = monthlySummary[m].by_genre;
        for (const [k, v] of Object.entries(bg)) genreMap[k] = (genreMap[k] || 0) + v;
      });
    } else {
      const m = monthlySummary[state.selectedMonth];
      if (m) genreMap = m.by_genre;
    }

    const sorted = Object.entries(genreMap).sort((a, b) => b[1] - a[1]);
    const maxVal = sorted.length > 0 ? sorted[0][1] : 1;
    const palette = ["#6366f1", "#10b981", "#f59e0b", "#ec4899", "#38bdf8"];

    elements.categoryGaugesList.innerHTML = sorted.slice(0, 5).map(([name, amount], idx) => {
      const pct = Math.min(100, Math.round((amount / maxVal) * 100));
      const color = palette[idx % palette.length];
      return `
        <div class="gauge-item">
          <div class="gauge-header">
            <span class="gauge-name">${escapeHtml(name)}</span>
            <span class="gauge-pct">¥${amount.toLocaleString()} (${pct}%)</span>
          </div>
          <div class="gauge-track">
            <div class="gauge-fill" style="width: ${pct}%; background-color: ${color}"></div>
          </div>
        </div>
      `;
    }).join("");
  }

  // --- テーブル描画 ---
  function renderDashboardRecentTable() {
    if (!state.transactions || state.transactions.length === 0) {
      elements.dashboardRecentTable.innerHTML = `<tr><td colspan="6" class="text-center">明細データがありません。インポートしてください。</td></tr>`;
      return;
    }
    const recent = state.transactions.slice(-6).reverse();
    elements.dashboardRecentTable.innerHTML = recent.map(t => `
      <tr>
        <td>${t.date}</td>
        <td><strong>${escapeHtml(t.description)}</strong></td>
        <td><span class="badge">${escapeHtml(t.source_name)}</span></td>
        <td><span class="badge genre-badge" onclick="openGenreModal('${t.date}', '${escapeJsString(t.description)}', ${t.amount}, '${escapeJsString(t.source_name)}', '${escapeJsString(t.genre)}')">${escapeHtml(t.genre)}</span></td>
        <td class="text-right ${t.type === 'INCOME' ? 'positive' : ''}">
          ${t.type === 'INCOME' ? '+' : ''}¥${t.amount.toLocaleString()}
        </td>
        <td>${t.is_internal_transfer ? '<span class="badge transfer">引落除外</span>' : ''}</td>
      </tr>
    `).join("");
    lucide.createIcons();
  }

  function renderGenreFilterOptions() {
    const genres = new Set(state.transactions.map(t => t.genre));
    const currentVal = elements.txGenreFilter.value;
    elements.txGenreFilter.innerHTML = '<option value="all">すべてのジャンル</option>';
    genres.forEach(g => {
      const opt = document.createElement("option");
      opt.value = g;
      opt.textContent = g;
      elements.txGenreFilter.appendChild(opt);
    });
    elements.txGenreFilter.value = currentVal;
  }

  function renderTransactionsTable() {
    const searchVal = elements.txSearchInput.value.toLowerCase();
    const genreVal = elements.txGenreFilter.value;

    const filtered = state.transactions.filter(t => {
      const matchesSearch = !searchVal || t.description.toLowerCase().includes(searchVal) || t.source_name.toLowerCase().includes(searchVal);
      const matchesGenre = genreVal === "all" || t.genre === genreVal;
      return matchesSearch && matchesGenre;
    });

    elements.txCountBadge.textContent = `${filtered.length} 件ヒット`;

    elements.fullTransactionsTable.innerHTML = filtered.map(t => `
      <tr>
        <td>${t.date}</td>
        <td><strong>${escapeHtml(t.description)}</strong></td>
        <td><span class="badge">${escapeHtml(t.source_name)}</span></td>
        <td><span class="badge genre-badge" onclick="openGenreModal('${t.date}', '${escapeJsString(t.description)}', ${t.amount}, '${escapeJsString(t.source_name)}', '${escapeJsString(t.genre)}')">${escapeHtml(t.genre)} ✏️</span></td>
        <td class="text-right ${t.type === 'INCOME' ? 'positive' : ''}">
          ${t.type === 'INCOME' ? '+' : ''}¥${t.amount.toLocaleString()}
        </td>
        <td>
          ${t.is_internal_transfer ? '<span class="badge transfer">引落除外</span>' : `<span class="badge ${t.type.toLowerCase()}">${t.type}</span>`}
        </td>
      </tr>
    `).join("");
    lucide.createIcons();
  }

  elements.txSearchInput.addEventListener("input", renderTransactionsTable);
  elements.txGenreFilter.addEventListener("change", renderTransactionsTable);

  // --- ジャンル編集モーダル ---
  window.openGenreModal = (date, description, amount, source_name, current_genre) => {
    state.editingTransaction = { date, description, amount, source_name };
    elements.modalTxDesc.textContent = description;
    elements.modalGenreInput.value = current_genre;
    elements.genreModal.classList.add("active");
  };

  function closeModal() {
    elements.genreModal.classList.remove("active");
    state.editingTransaction = null;
  }

  elements.btnCloseModal.addEventListener("click", closeModal);
  elements.btnCancelModal.addEventListener("click", closeModal);

  elements.btnConfirmModal.addEventListener("click", async () => {
    if (!state.editingTransaction) return;
    const newGenre = elements.modalGenreInput.value.trim();
    if (!newGenre) return;

    try {
      const res = await fetch("/api/transactions/update", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...state.editingTransaction,
          new_genre: newGenre
        })
      });
      const result = await res.json();
      if (result.status === "success") {
        showToast("ジャンルを更新しました。");
        closeModal();
        await fetchSummary();
        await fetchTransactions();
      }
    } catch (err) {
      showToast("ジャンル更新エラー: " + err, "error");
    }
  });

  // --- インポート ---
  async function triggerImport() {
    elements.importLogConsole.textContent = "[スキャン中] resources/ フォルダのCSVを読み込んでいます...";
    try {
      const res = await fetch("/api/import", { method: "POST" });
      const data = await res.json();
      if (data.status === "success") {
        elements.importLogConsole.textContent = `[完了] ${data.added_count} 件の新しい取引を追加しました。\n` + data.logs.join("\n");
        showToast(`${data.added_count} 件の新取引を同期しました。`);
        await fetchSummary();
        await fetchTransactions();
      }
    } catch (err) {
      elements.importLogConsole.textContent = "[エラー] インポート処理に失敗しました: " + err;
      showToast("インポートエラー: " + err, "error");
    }
  }

  elements.btnQuickImport.addEventListener("click", triggerImport);
  elements.btnStartImport.addEventListener("click", triggerImport);

  // --- ルール ---
  function renderRulesEditor() {
    elements.prefixRulesList.innerHTML = Object.entries(state.rules.prefix_rules).map(([prefix, genre], idx) => `
      <div class="rule-item-row" data-type="prefix" data-idx="${idx}">
        <input type="text" class="rule-key" value="${escapeHtml(prefix)}" placeholder="例: ＡＭＡＺＯΝ">
        <span class="arrow-icon">➔</span>
        <input type="text" class="rule-val" value="${escapeHtml(genre)}" placeholder="ジャンル名">
        <button class="btn-icon-danger" onclick="removeRuleRow(this)"><i data-lucide="trash-2"></i></button>
      </div>
    `).join("");

    elements.keywordRulesList.innerHTML = Object.entries(state.rules.keyword_rules).map(([keyword, genre], idx) => `
      <div class="rule-item-row" data-type="keyword" data-idx="${idx}">
        <input type="text" class="rule-key" value="${escapeHtml(keyword)}" placeholder="例: 山岡家">
        <span class="arrow-icon">➔</span>
        <input type="text" class="rule-val" value="${escapeHtml(genre)}" placeholder="ジャンル名">
        <button class="btn-icon-danger" onclick="removeRuleRow(this)"><i data-lucide="trash-2"></i></button>
      </div>
    `).join("");

    lucide.createIcons();
  }

  window.removeRuleRow = (btn) => {
    btn.closest(".rule-item-row").remove();
  };

  elements.btnAddPrefixRule.addEventListener("click", () => {
    const div = document.createElement("div");
    div.className = "rule-item-row";
    div.dataset.type = "prefix";
    div.innerHTML = `
      <input type="text" class="rule-key" placeholder="前方一致キーワード">
      <span class="arrow-icon">➔</span>
      <input type="text" class="rule-val" placeholder="ジャンル名">
      <button class="btn-icon-danger" onclick="removeRuleRow(this)"><i data-lucide="trash-2"></i></button>
    `;
    elements.prefixRulesList.appendChild(div);
    lucide.createIcons();
  });

  elements.btnAddKeywordRule.addEventListener("click", () => {
    const div = document.createElement("div");
    div.className = "rule-item-row";
    div.dataset.type = "keyword";
    div.innerHTML = `
      <input type="text" class="rule-key" placeholder="部分一致キーワード">
      <span class="arrow-icon">➔</span>
      <input type="text" class="rule-val" placeholder="ジャンル名">
      <button class="btn-icon-danger" onclick="removeRuleRow(this)"><i data-lucide="trash-2"></i></button>
    `;
    elements.keywordRulesList.appendChild(div);
    lucide.createIcons();
  });

  elements.btnSaveRules.addEventListener("click", async () => {
    const newPrefixRules = {};
    elements.prefixRulesList.querySelectorAll(".rule-item-row").forEach(row => {
      const k = row.querySelector(".rule-key").value.trim();
      const v = row.querySelector(".rule-val").value.trim();
      if (k && v) newPrefixRules[k] = v;
    });

    const newKeywordRules = {};
    elements.keywordRulesList.querySelectorAll(".rule-item-row").forEach(row => {
      const k = row.querySelector(".rule-key").value.trim();
      const v = row.querySelector(".rule-val").value.trim();
      if (k && v) newKeywordRules[k] = v;
    });

    const payload = {
      prefix_rules: newPrefixRules,
      keyword_rules: newKeywordRules,
      default_genre: state.rules.default_genre || "未分類"
    };

    try {
      const res = await fetch("/api/rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      showToast(data.message || "分類ルールを保存・再適用しました。");
      await fetchSummary();
      await fetchTransactions();
    } catch (err) {
      showToast("ルール保存エラー: " + err, "error");
    }
  });

  function escapeHtml(str) {
    if (!str) return "";
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  function escapeJsString(str) {
    if (!str) return "";
    return str.replace(/\\/g, "\\\\").replace(/'/g, "\\'");
  }

  // 初期化ロード
  fetchProfiles();
  fetchSummary();
  fetchTransactions();
  fetchRules();
});
