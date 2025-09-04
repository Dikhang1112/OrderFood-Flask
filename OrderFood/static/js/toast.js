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
window.Toast.warningConfirm = function(message, onConfirm, onCancel) {
  const stack = document.getElementById("toast-stack") || (()=>{
    const el = document.createElement("div");
    el.id = "toast-stack";
    document.body.appendChild(el);
    return el;
  })();
  const div = document.createElement("div");
  div.className = "toast warning";
  div.innerHTML = `
    <div>
      <div class="t-title">Xác nhận</div>
      <div class="t-msg">${message}</div>
      <div style="margin-top:8px; display:flex; gap:8px;">
       <button class="btn-ok"
              style="background:#16a34a;color:#fff;border:none;border-radius:8px;
                     padding:6px 12px;cursor:pointer;">
        Đồng ý
      </button>
      <button class="btn-cancel"
              style="background:#2563eb;color:#fff;border:none;border-radius:8px;
                     padding:6px 12px;cursor:pointer;">
        Hủy
      </button>
      </div>
    </div>
  `;
  stack.appendChild(div);
  requestAnimationFrame(()=>div.classList.add("show"));
  const close = ()=>{ div.classList.remove("show"); setTimeout(()=>div.remove(),180); };
  div.querySelector(".btn-ok").onclick = ()=>{ close(); if(onConfirm) onConfirm(); };
  div.querySelector(".btn-cancel").onclick = ()=>{ close(); if(onCancel) onCancel(); };
};
