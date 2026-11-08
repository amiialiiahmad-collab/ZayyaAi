let activeChat = null;
const messagesEl = document.getElementById("messages");
const welcome = document.getElementById("welcome");
const historyEl = document.getElementById("history");
const promptEl = document.getElementById("prompt");
const composer = document.getElementById("composer");

function showWelcome(show){ welcome.style.display = show ? "block" : "none"; }
function addMessage(role, content){
  const row=document.createElement("div"); row.className="message "+role;
  const avatar=document.createElement("div"); avatar.className="avatar"; avatar.textContent=role==="assistant"?"Z":"Y";
  const body=document.createElement("div"); body.className="message-content"; body.textContent=content;
  row.append(avatar,body); messagesEl.append(row);
}
function addHistory(id,title){
  let item=historyEl.querySelector(`[data-id="${id}"]`);
  if(!item){ item=document.createElement("button"); item.className="history-item"; item.dataset.id=id; historyEl.prepend(item); }
  item.textContent=title || "New chat";
  document.querySelectorAll(".history-item").forEach(x=>x.classList.toggle("active",x.dataset.id==id));
}
async function newChat(){
  const r=await fetch("/api/chats",{method:"POST"});
  const data=await r.json(); if(!r.ok){alert(data.error||"Could not create chat");return;}
  activeChat=data.id; messagesEl.innerHTML=""; showWelcome(true); addHistory(data.id,data.title); promptEl.focus();
}
async function openChat(id){
  const r=await fetch(`/api/chats/${id}`); const data=await r.json();
  if(!r.ok){alert(data.error||"Could not open chat");return;}
  activeChat=id; messagesEl.innerHTML=""; showWelcome(data.messages.length===0);
  data.messages.forEach(m=>addMessage(m.role,m.content)); addHistory(id,data.title);
  document.getElementById("sidebar").classList.remove("open");
}
document.getElementById("newChat").addEventListener("click",newChat);
historyEl.addEventListener("click",e=>{const item=e.target.closest("[data-id]");if(item)openChat(item.dataset.id);});
document.querySelectorAll("[data-prompt]").forEach(b=>b.addEventListener("click",()=>{promptEl.value=b.dataset.prompt;promptEl.focus();}));
composer.addEventListener("submit",async e=>{
  e.preventDefault(); const text=promptEl.value.trim(); if(!text)return;
  if(!activeChat){await newChat(); if(!activeChat)return;}
  showWelcome(false); addMessage("user",text); promptEl.value=""; promptEl.style.height="auto";
  const pending=document.createElement("div"); pending.className="message"; pending.textContent="ZAYYA AI is thinking…"; messagesEl.append(pending);
  document.getElementById("sendBtn").disabled=true;
  try{
    const r=await fetch(`/api/chats/${activeChat}/messages`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:text})});
    const data=await r.json(); pending.remove();
    if(!r.ok){addMessage("assistant",data.error||"Something went wrong.");}
    else{addMessage("assistant",data.reply);addHistory(activeChat,data.title);}
  }catch(err){pending.remove();addMessage("assistant","Network error. Please try again.");}
  document.getElementById("sendBtn").disabled=false;
});
promptEl.addEventListener("input",()=>{promptEl.style.height="auto";promptEl.style.height=Math.min(promptEl.scrollHeight,150)+"px";});
promptEl.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();composer.requestSubmit();}});
document.getElementById("themeToggle").addEventListener("click",()=>document.body.classList.toggle("light"));
document.getElementById("menuBtn").addEventListener("click",()=>document.getElementById("sidebar").classList.toggle("open"));
