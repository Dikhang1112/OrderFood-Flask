(function(){
  const stackId = "toast-stack";
  function ensureStack(){
    let el = document.getElementById(stackId);
    if(!el){
      el = document.createElement("div");
      el.id = stackId;
      document.body.appendChild(el);
    }
    return el;
  }
  function makeToast(type, msg, title){
    const stack = ensureStack();
    const div = document.createElement("div");
    div.className = "toast " + (type || "success");
    div.innerHTML = `
      <div>
        <div class="t-title">${title || (type==='success'?'Thành công': type==='error'?'Lỗi':'Cảnh báo')}</div>
        <div class="t-msg">${msg || ""}</div>
      </div>
      <button class="t-close" aria-label="Đóng">&times;</button>
    `;
    stack.appendChild(div);
    requestAnimationFrame(()=>div.classList.add("show"));
    const close = ()=>{ div.classList.remove("show"); setTimeout(()=>div.remove(),180); };
    div.querySelector(".t-close").onclick = close;
    setTimeout(close, 3500);
  }
  window.Toast = {
    success: (m,t)=>makeToast("success", m, t),
    error:   (m,t)=>makeToast("error",   m, t),
    warning: (m,t)=>makeToast("warning", m, t),
    show:    (o)=>makeToast(o.type||"success", o.message||o.msg||"", o.title||"")
  };

  // Hiển thị flash message từ server
  try{
    const flashes = window.__flashes || [];
    flashes.forEach(([cat, msg])=>{
      const type = (cat||"").toLowerCase();
      if(type==="success"||type==="error"||type==="warning")
        window.Toast.show({type, message: msg});
      else
        window.Toast.show({type:"success", message: msg});
    });
  }catch(e){}
})();
// === Xác nhận (có 2 nút) ===
window.Toast.warningConfirm = function(message, onConfirm, onCancel){
  const stack = document.getElementById("toast-stack") || (() => {
    const el = document.createElement("div"); el.id = "toast-stack"; document.body.appendChild(el); return el;
  })();
  const div = document.createElement("div");
  div.className = "toast warning";
  div.innerHTML = `
    <div style="width:360px;max-width:90vw">
      <div class="t-title">Xác nhận</div>
      <div class="t-msg">${message || "Bạn có chắc?"}</div>
      <div style="margin-top:10px;display:flex;gap:8px;justify-content:flex-end">
        <button class="btn-ok"
                style="background:#16a34a;color:#fff;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;">
          Đồng ý
        </button>
        <button class="btn-cancel"
                style="background:#2563eb;color:#fff;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;">
          Hủy
        </button>
      </div>
    </div>`;
  stack.appendChild(div);
  requestAnimationFrame(()=>div.classList.add("show"));
  const close = () => { div.classList.remove("show"); setTimeout(()=>div.remove(),180); };
  div.querySelector(".btn-ok").onclick = () => { close(); if(typeof onConfirm==="function") onConfirm(); };
  div.querySelector(".btn-cancel").onclick = () => { close(); if(typeof onCancel==="function") onCancel(); };
};

// === Prompt nhập lý do ===
window.Toast.warningPrompt = function(title, placeholder, onSubmit, onCancel){
  const stack = document.getElementById("toast-stack") || (() => {
    const el = document.createElement("div"); el.id = "toast-stack"; document.body.appendChild(el); return el;
  })();
  const div = document.createElement("div");
  div.className = "toast warning";
  div.innerHTML = `
    <div style="width:360px;max-width:90vw">
      <div class="t-title">${title || "Lí do"}</div>
      <div class="t-msg" style="margin-bottom:8px">Vui lòng nhập lý do từ chối.</div>
      <input type="text" class="t-input" placeholder="${placeholder || "Nhập lý do..."}"
             style="width:100%;padding:8px 10px;border:1px solid rgba(0,0,0,.15);border-radius:8px;outline:none" />
      <div style="margin-top:10px;display:flex;gap:8px;justify-content:flex-end">
        <button class="btn-ok"
                style="background:#16a34a;color:#fff;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;">
          Đồng ý
        </button>
        <button class="btn-cancel"
                style="background:#2563eb;color:#fff;border:none;border-radius:8px;padding:6px 12px;cursor:pointer;">
          Hủy
        </button>
      </div>
    </div>`;
  stack.appendChild(div);
  requestAnimationFrame(()=>div.classList.add("show"));
  const input = div.querySelector(".t-input");
  const close = () => { div.classList.remove("show"); setTimeout(()=>div.remove(),180); };
  const submit = () => {
    const val = (input.value || "").trim();
    if (!val) { input.focus(); return; }
    close(); if(typeof onSubmit==="function") onSubmit(val);
  };
  div.querySelector(".btn-ok").onclick = submit;
  div.querySelector(".btn-cancel").onclick = () => { close(); if(typeof onCancel==="function") onCancel(); };
  input.addEventListener("keydown", e => { if(e.key==="Enter") submit(); });
  input.focus();
};
