const API = '';

async function jsonFetch(path, options = {}) {
  const res = await fetch(API + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || res.statusText);
  return res.json();
}

let currentDraftId = null;

document.getElementById('btnGenerate').addEventListener('click', async () => {
  const userInput = document.getElementById('userInput').value.trim() || null;
  const status = document.getElementById('generateStatus');
  status.textContent = 'Generating…';
  document.getElementById('btnGenerate').disabled = true;
  try {
    const data = await jsonFetch('/generate', {
      method: 'POST',
      body: JSON.stringify({ user_input: userInput || null }),
    });
    currentDraftId = data.draft_id;
    const p = data.post_preview || {};
    document.getElementById('previewHook').textContent = p.hook || '';
    document.getElementById('previewBody').textContent = p.body || '';
    document.getElementById('previewCta').textContent = p.cta || '';
    document.getElementById('previewHashtags').textContent = p.hashtags || '';
    const imgWrap = document.getElementById('previewImageWrap');
    const imgFallback = document.getElementById('previewImageFallback');
    const img = document.getElementById('previewImage');
    // Only show image if API returned image_url (don't request /storage/id when no image was generated)
    const imageUrl = data.image_url || null;
    if (imageUrl) {
      img.src = imageUrl + (imageUrl.indexOf('?') === -1 ? '?t=' + Date.now() : '&t=' + Date.now());
      imgWrap.hidden = false;
      if (imgFallback) { imgFallback.hidden = true; }
    } else {
      imgWrap.hidden = true;
      if (imgFallback) { imgFallback.hidden = false; imgFallback.textContent = 'Optional: click "Generate image" to create an image for this post.'; }
    }
    document.getElementById('previewSection').hidden = false;
    document.getElementById('btnRegenerate').disabled = false;
    document.getElementById('btnPublish').disabled = !document.getElementById('accountSelect').value;
    status.textContent = data.message || 'Ready for review.';
    loadAccounts();
    loadDrafts();
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
  } finally {
    document.getElementById('btnGenerate').disabled = false;
  }
});

document.getElementById('btnRegenerate').addEventListener('click', async () => {
  if (!currentDraftId) return;
  const status = document.getElementById('generateStatus');
  status.textContent = 'Regenerating…';
  document.getElementById('btnRegenerate').disabled = true;
  try {
    const data = await jsonFetch('/generate', {
      method: 'POST',
      body: JSON.stringify({ regenerate_draft_id: currentDraftId }),
    });
    currentDraftId = data.draft_id;
    const p = data.post_preview || {};
    document.getElementById('previewHook').textContent = p.hook || '';
    document.getElementById('previewBody').textContent = p.body || '';
    document.getElementById('previewCta').textContent = p.cta || '';
    document.getElementById('previewHashtags').textContent = p.hashtags || '';
    const imgWrap = document.getElementById('previewImageWrap');
    const imgFallback = document.getElementById('previewImageFallback');
    const img = document.getElementById('previewImage');
    const imageUrl = data.image_url || null;
    if (imageUrl) {
      img.src = imageUrl + (imageUrl.indexOf('?') === -1 ? '?t=' + Date.now() : '&t=' + Date.now());
      if (imgWrap) imgWrap.hidden = false;
      if (imgFallback) imgFallback.hidden = true;
    } else {
      if (imgWrap) imgWrap.hidden = true;
      if (imgFallback) { imgFallback.hidden = false; imgFallback.textContent = 'Optional: click "Generate image" to create an image for this post.'; }
    }
    document.getElementById('previewSection').hidden = false;
    status.textContent = data.message || 'Regenerated.';
    loadDrafts();
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
  } finally {
    document.getElementById('btnRegenerate').disabled = false;
  }
});

document.getElementById('btnGenerateImage').addEventListener('click', async () => {
  if (!currentDraftId) return;
  const status = document.getElementById('generateStatus');
  const imgWrap = document.getElementById('previewImageWrap');
  const imgFallback = document.getElementById('previewImageFallback');
  const img = document.getElementById('previewImage');
  status.textContent = 'Generating image…';
  document.getElementById('btnGenerateImage').disabled = true;
  try {
    const data = await jsonFetch('/post-history/drafts/' + currentDraftId + '/generate-image', { method: 'POST' });
    if (data.image_url) {
      img.src = data.image_url + (data.image_url.indexOf('?') === -1 ? '?t=' + Date.now() : '&t=' + Date.now());
      imgWrap.hidden = false;
      if (imgFallback) imgFallback.hidden = true;
      status.textContent = 'Image generated.';
    } else {
      if (imgFallback) { imgFallback.hidden = false; imgFallback.textContent = data.message || 'Image could not be generated. You can still publish the text.'; }
      status.textContent = data.message || 'Image not generated.';
    }
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
    if (imgFallback) { imgFallback.hidden = false; imgFallback.textContent = 'Image generation failed: ' + e.message; }
  } finally {
    document.getElementById('btnGenerateImage').disabled = false;
  }
});

document.getElementById('btnEdit').addEventListener('click', () => {
  document.getElementById('previewBoxReadonly').hidden = true;
  document.getElementById('previewBoxEdit').hidden = false;
  document.getElementById('btnEdit').hidden = true;
  document.getElementById('btnSaveEdit').hidden = false;
  document.getElementById('editHook').value = document.getElementById('previewHook').textContent;
  document.getElementById('editBody').value = document.getElementById('previewBody').textContent;
  document.getElementById('editCta').value = document.getElementById('previewCta').textContent;
  document.getElementById('editHashtags').value = document.getElementById('previewHashtags').textContent;
});

document.getElementById('btnSaveEdit').addEventListener('click', async () => {
  if (!currentDraftId) return;
  const status = document.getElementById('generateStatus');
  status.textContent = 'Saving…';
  try {
    await jsonFetch('/post-history/drafts/' + currentDraftId, {
      method: 'PATCH',
      body: JSON.stringify({
        hook: document.getElementById('editHook').value,
        body: document.getElementById('editBody').value,
        cta: document.getElementById('editCta').value,
        hashtags: document.getElementById('editHashtags').value,
      }),
    });
    document.getElementById('previewHook').textContent = document.getElementById('editHook').value;
    document.getElementById('previewBody').textContent = document.getElementById('editBody').value;
    document.getElementById('previewCta').textContent = document.getElementById('editCta').value;
    document.getElementById('previewHashtags').textContent = document.getElementById('editHashtags').value;
    document.getElementById('previewBoxEdit').hidden = true;
    document.getElementById('previewBoxReadonly').hidden = false;
    document.getElementById('btnSaveEdit').hidden = true;
    document.getElementById('btnEdit').hidden = false;
    status.textContent = 'Edits saved.';
    loadDrafts();
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
  }
});

document.getElementById('btnPublish').addEventListener('click', async () => {
  const draftId = currentDraftId;
  const accountId = document.getElementById('accountSelect').value;
  if (!draftId || !accountId) return;
  const status = document.getElementById('publishStatus');
  status.textContent = 'Publishing…';
  document.getElementById('btnPublish').disabled = true;
  try {
    const data = await jsonFetch('/publish', {
      method: 'POST',
      body: JSON.stringify({ draft_id: draftId, account_id: parseInt(accountId, 10) }),
    });
    status.textContent = data.status === 'published'
      ? 'Published. LinkedIn ID: ' + (data.linkedin_post_id || '—')
      : 'Scheduled for ' + (data.scheduled_at || 'later');
    loadDrafts();
    loadScheduled();
    loadPostHistory();
    loadAnalytics();
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
  } finally {
    document.getElementById('btnPublish').disabled = false;
  }
});

async function loadAccounts() {
  const sel = document.getElementById('accountSelect');
  const current = sel.value;
  try {
    const list = await jsonFetch('/accounts');
    sel.innerHTML = '<option value="">— Select account —</option>' +
      list.map(a => `<option value="${a.id}">${a.display_name} (${a.account_type})</option>`).join('');
    if (current) sel.value = current;
    document.getElementById('btnPublish').disabled = !currentDraftId || !sel.value;
  } catch (e) {
    sel.innerHTML = '<option value="">— Select account —</option>';
    var statusEl = document.getElementById('connectStatus');
    if (statusEl) statusEl.textContent = 'Could not load accounts: ' + (e.message || 'check server');
  }
}

function connectLinkedIn(accountType) {
  const status = document.getElementById('connectStatus');
  status.textContent = 'Redirecting to LinkedIn…';
  jsonFetch('/accounts/auth/linkedin?account_type=' + accountType)
    .then(data => {
      if (data.authorization_url) {
        window.location.href = data.authorization_url;
      } else {
        status.textContent = 'Could not get LinkedIn login URL.';
      }
    })
    .catch(e => {
      status.textContent = 'Error: ' + e.message;
    });
}

document.getElementById('btnConnectPersonal').addEventListener('click', () => connectLinkedIn('personal'));
document.getElementById('btnConnectCompany').addEventListener('click', () => connectLinkedIn('company'));

async function loadAnalytics() {
  const el = document.getElementById('analyticsContent');
  try {
    const a = await jsonFetch('/analytics');
    el.innerHTML = `
      <div class="analytics-grid">
        <div class="analytics-item"><strong>${a.total_posts}</strong> posts</div>
        <div class="analytics-item"><strong>${a.total_impressions}</strong> impressions</div>
        <div class="analytics-item"><strong>${(a.avg_engagement_rate || 0).toFixed(1)}%</strong> avg engagement</div>
      </div>
      <p style="margin-top:0.75rem;font-size:0.9rem;">Best days: ${(a.best_days || []).join(', ') || '—'}. Best times: ${(a.best_times || []).join(', ') || '—'}.</p>
    `;
  } catch (_) {
    el.textContent = 'No analytics yet.';
  }
}

function escapeHtml(s) {
  if (s == null) return '';
  const t = String(s);
  return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function loadDraftIntoPreview(draftId) {
  const status = document.getElementById('generateStatus');
  status.textContent = 'Loading draft…';
  try {
    const d = await jsonFetch('/post-history/drafts/' + draftId);
    currentDraftId = d.id;
    document.getElementById('previewHook').textContent = d.hook || '';
    document.getElementById('previewBody').textContent = d.body || '';
    document.getElementById('previewCta').textContent = d.cta || '';
    document.getElementById('previewHashtags').textContent = d.hashtags || '';
    document.getElementById('editHook').value = d.hook || '';
    document.getElementById('editBody').value = d.body || '';
    document.getElementById('editCta').value = d.cta || '';
    document.getElementById('editHashtags').value = d.hashtags || '';
    document.getElementById('previewBoxEdit').hidden = true;
    document.getElementById('previewBoxReadonly').hidden = false;
    document.getElementById('btnSaveEdit').hidden = true;
    document.getElementById('btnEdit').hidden = false;
    document.getElementById('previewSection').hidden = false;
    document.getElementById('btnRegenerate').disabled = false;
    document.getElementById('btnPublish').disabled = !document.getElementById('accountSelect').value;
    loadAccounts();
    status.textContent = 'Draft loaded. Edit if needed, then choose an account and Publish.';
  } catch (e) {
    status.textContent = 'Error: ' + e.message;
  }
}

async function loadDrafts() {
  const el = document.getElementById('draftsContent');
  try {
    const list = await jsonFetch('/post-history/drafts');
    el.innerHTML = list.length
      ? list.slice(0, 10).map(d => {
          const snippet = escapeHtml((d.hook || '').slice(0, 80)) + '…';
          return `
          <div class="draft-item" data-draft-id="${d.id}">
            <strong>Draft #${d.id}</strong>
            <div class="snippet">${snippet}</div>
            <button type="button" class="btn btn-secondary btn-use-draft" data-draft-id="${d.id}">Use this draft</button>
          </div>`;
        }).join('')
      : 'No drafts yet.';
    el.querySelectorAll('.btn-use-draft').forEach(btn => {
      btn.addEventListener('click', () => loadDraftIntoPreview(parseInt(btn.getAttribute('data-draft-id'), 10)));
    });
  } catch (_) {
    el.textContent = 'Could not load drafts.';
  }
}

async function loadScheduled() {
  const el = document.getElementById('scheduledContent');
  try {
    const list = await jsonFetch('/post-history/scheduled');
    el.innerHTML = list.length
      ? list.map(s => `<div class="history-item">Draft #${s.draft_id} → ${s.scheduled_at} (${s.status})</div>`).join('')
      : 'No scheduled posts.';
  } catch (_) {
    el.textContent = 'Could not load scheduled.';
  }
}

async function loadPostHistory() {
  const el = document.getElementById('historyContent');
  try {
    const list = await jsonFetch('/post-history');
    el.innerHTML = list.length
      ? list.map(p => {
          const date = p.published_at ? new Date(p.published_at).toLocaleString() : '—';
          const impressions = p.impressions != null ? p.impressions : '—';
          const engagement = p.engagement_rate != null ? (p.engagement_rate * 100).toFixed(1) + '%' : '—';
          const snippet = (p.content_text || '').slice(0, 100) + ((p.content_text || '').length > 100 ? '…' : '');
          return `<div class="history-item"><strong>${date}</strong><div class="snippet">${snippet}</div><small>Impressions: ${impressions} · Engagement: ${engagement}</small></div>`;
        }).join('')
      : 'No published posts yet.';
  } catch (_) {
    el.textContent = 'Could not load published posts.';
  }
}

// On load: check for OAuth callback params and refresh accounts
(function checkCallback() {
  const params = new URLSearchParams(window.location.search);
  if (params.get('connected') === '1') {
    loadAccounts();
    const status = document.getElementById('connectStatus');
    if (status) status.textContent = 'Account connected. Select it above to publish.';
    window.history.replaceState({}, document.title, window.location.pathname);
  }
  if (params.get('error') === 'linkedin') {
    const msg = params.get('message') || 'LinkedIn connection failed.';
    const status = document.getElementById('connectStatus');
    if (status) status.textContent = msg;
    window.history.replaceState({}, document.title, window.location.pathname);
  }
})();

loadAccounts();
loadAnalytics();
loadDrafts();
loadScheduled();
loadPostHistory();
