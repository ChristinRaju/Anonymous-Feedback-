console.log("✅ chat.js loaded");


const socket = io();

// DOM elements
const serverSidebar = document.getElementById('server-sidebar');
const channelList = document.getElementById('channel-list');
const chatHeader = document.getElementById('chat-header');
const messagesDiv = document.getElementById('messages');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');
const typingIndicator = document.getElementById('typing-indicator');
const userListDiv = document.getElementById('user-list');
const addServerBtn = document.getElementById('add-server');
const profileBtn = document.getElementById('profile-btn');
const profileModal = document.getElementById('profile-modal');
const profileNickname = document.getElementById('profile-nickname');
const profileAvatar = document.getElementById('profile-avatar');
const profileStatus = document.getElementById('profile-status');
const profileSave = document.getElementById('profile-save');
const profileCancel = document.getElementById('profile-cancel');
const themeToggle = document.getElementById('theme-toggle');
const pinnedBar = document.getElementById('pinned-bar');
const addServerModal = document.getElementById('add-server-modal');
const addServerName = document.getElementById('add-server-name');
const addServerSave = document.getElementById('add-server-save');
const addServerCancel = document.getElementById('add-server-cancel');
const addChannelModal = document.getElementById('add-channel-modal');
const addChannelName = document.getElementById('add-channel-name');
const addChannelSave = document.getElementById('add-channel-save');
const addChannelCancel = document.getElementById('add-channel-cancel');

let myUsername = '';
let myAvatar = '';
let currentServer = null;
let currentChannel = null;
let typingTimeout = null;
let myStatus = '';

function renderChannels(channels) {
  channelList.innerHTML = '';
  channels.forEach(channel => {
    const div = document.createElement('div');
    div.className = 'channel' + (channel === currentChannel ? ' selected' : '');
    div.textContent = `# ${channel}`;
    div.onclick = () => {
      if (currentChannel !== channel) {
        currentChannel = channel;
        socket.emit('join_channel', { server: currentServer, channel });
        renderChannels(channels);
        messagesDiv.innerHTML = '';
        chatHeader.textContent = `${currentServer} / #${channel}`;
        chatForm.style.display = '';
      }
    };
    channelList.appendChild(div);
  });
  // Add channel creation
  const addChannel = document.createElement('div');
  addChannel.className = 'channel';
  addChannel.style.color = '#5865f2';
  addChannel.textContent = '+ Add Channel';
  addChannel.onclick = () => {
    addChannelName.value = '';
    addChannelModal.style.display = 'flex';
    setTimeout(() => addChannelName.focus(), 100);
  };
  channelList.appendChild(addChannel);
}

function renderUserList(users) {
  userListDiv.innerHTML = '';
  users.forEach(user => {
    const div = document.createElement('div');
    div.className = 'user';
    const statusDot = document.createElement('span');
    statusDot.style.display = 'inline-block';
    statusDot.style.width = '10px';
    statusDot.style.height = '10px';
    statusDot.style.borderRadius = '50%';
    statusDot.style.marginRight = '0.5em';
    statusDot.style.background = user.online ? '#43b581' : '#747f8d';
    statusDot.title = user.online ? 'Online' : (user.last_seen ? 'Last seen: ' + formatTimestamp(user.last_seen) : 'Offline');
    div.appendChild(statusDot);
    div.innerHTML += `<span class="avatar" title="${user.status || ''}">${user.avatar}</span> <span title="${user.status || ''}">${user.username}</span>`;
    if (user.status) {
      div.title = user.status;
    }
    if (!user.online && user.last_seen) {
      div.title += (div.title ? ' | ' : '') + 'Last seen: ' + formatTimestamp(user.last_seen);
    }
    userListDiv.appendChild(div);
  });
}

  
// --- Socket.IO Events ---

socket.on('server_deleted', ({ server }) => {
  console.log('Server deleted:', server);

  // Remove server from sidebar
  const serverElement = document.querySelector(`[data-server-name="${server}"]`);
  if (serverElement) {
    serverElement.remove();
  }
});
function highlightMentions(text) {
  // Simple placeholder implementation: return text as is
  return text;
}

socket.on('session', data => {
  myUsername = data.username;
  myAvatar = data.avatar;
  myStatus = data.status || '';
});

socket.on('connect', () => {
  console.log('🔌 Connected to Socket.IO server');
});

console.log('[DEBUG] Waiting for server_list...');
socket.on('server_list', data => {
  console.log('[RECEIVED] server_list:', data.servers);
  renderServers(data.servers);
  // Automatically select the first server if none selected
  if (!currentServer && data.servers.length > 0) {
    currentServer = data.servers[0];
    socket.emit('join_server', { server: currentServer });
  }
});

socket.on('channel_list', data => {
  renderChannels(data.channels);
  // Automatically select the first channel if none selected
  if (!currentChannel && data.channels.length > 0) {
    currentChannel = data.channels[0];
    chatHeader.textContent = `${currentServer} / #${currentChannel}`;
    chatForm.style.display = '';
  }
});

socket.on('joined_channel', data => {
  chatHeader.textContent = `${currentServer} / #${data.channel}`;
  chatForm.style.display = '';
  messagesDiv.innerHTML = '';
});

socket.on('typing', data => {
  typingIndicator.textContent = `${data.user} is typing...`;
  typingIndicator.style.display = '';
  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(() => {
    typingIndicator.style.display = 'none';
  }, 1200);
});

// Store the latest user list for status lookup in messages
let latestUserList = [];
socket.on('user_list', data => {
  latestUserList = data.users;
  renderUserList(data.users);
});

function getUserStatus(username, avatar) {
  const user = latestUserList.find(u => u.username === username && u.avatar === avatar);
  return user ? { online: user.online, last_seen: user.last_seen } : { online: false, last_seen: null };
}

socket.on('profile_updated', data => {
  myUsername = data.username;
  myAvatar = data.avatar;
  myStatus = data.status || '';
});

// --- UI Events ---
chatForm.addEventListener('submit', function(e) {
  console.log('[DEBUG] Form submit event triggered');
  e.preventDefault();
  const msg = messageInput.value.trim();
  if (msg && currentServer && currentChannel) {
    // Generate a temporary unique id for the message
    const tempId = 'temp-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
    // Add the message to messageHistory and render immediately
    messageHistory.push({
      username: myUsername,
      avatar: myAvatar,
      text: msg,
      self: true,
      id: tempId,
      timestamp: new Date().toISOString(),
      status: ''
    });
    renderMessages(messageHistory);
    // Emit the message to the server
    socket.emit('message', {
      msg,
      username: myUsername,
      avatar: myAvatar,
      server: currentServer,
      channel: currentChannel
    });
    messageInput.value = '';
  } else {
    alert('Please select a server and channel before sending a message.');
  }
});

messageInput.addEventListener('input', function() {
  if (currentServer && currentChannel) {
    socket.emit('typing', {});
  }
});

addServerBtn.onclick = () => {
  addServerName.value = '';
  addServerModal.style.display = 'flex';
  setTimeout(() => addServerName.focus(), 100);
};
addServerCancel.onclick = () => {
  addServerModal.style.display = 'none';
};
addServerSave.onclick = () => {
  const name = addServerName.value.trim();
  if (name) {
    console.log("Emitting create_server event with server name:", name);
    socket.emit('create_server', { server: name });
    addServerModal.style.display = 'none';
    setTimeout(() => socket.emit('get_server_list'), 500);
  } else {
    addServerName.focus();
  }
};
socket.on('server_list', data => {
  console.log('[RECEIVED] server_list:', data.servers);
  renderServers(data.servers);
  // Automatically select the newly added server if not already selected
  if (data.servers.length > 0) {
    const newServer = data.servers[data.servers.length - 1];
    if (currentServer !== newServer) {
      currentServer = newServer;
      socket.emit('join_server', { server: newServer });
    }
  }
});
addServerName.onkeydown = (e) => {
  if (e.key === 'Enter') addServerSave.onclick();
  if (e.key === 'Escape') addServerCancel.onclick();
};

addChannelCancel.onclick = () => {
  addChannelModal.style.display = 'none';
};
addChannelSave.onclick = () => {
  const name = addChannelName.value.trim();
  if (name && currentServer) {
    socket.emit('create_channel', { server: currentServer, channel: name });
    addChannelModal.style.display = 'none';
  } else {
    addChannelName.focus();
  }
};
addChannelName.onkeydown = (e) => {
  if (e.key === 'Enter') addChannelSave.onclick();
  if (e.key === 'Escape') addChannelCancel.onclick();
};

// Animated transitions for modals
function showModal(modal) {
  modal.style.display = 'flex';
  modal.classList.add('fade-in');
  setTimeout(() => modal.classList.remove('fade-in'), 400);
}
function hideModal(modal) {
  modal.style.display = 'none';
}
profileBtn.onclick = () => {
  profileNickname.value = myUsername;
  profileAvatar.value = myAvatar;
  profileStatus.value = myStatus;
  showModal(profileModal);
};
profileCancel.onclick = () => {
  hideModal(profileModal);
};
profileSave.onclick = () => {
  const username = profileNickname.value.trim() || myUsername;
  const avatar = profileAvatar.value.trim() || myAvatar;
  const status = profileStatus.value.trim();
  socket.emit('update_profile', { username, avatar, status });
  hideModal(profileModal);
};

// --- Message Rendering ---
function editMessage(msgId, div, oldMsg) {
  const input = document.createElement('input');
  input.type = 'text';
  input.value = oldMsg;
  input.style.flex = '1';
  div.querySelector('.msg-text').replaceWith(input);
  input.focus();

  // Remove previous event handlers to allow multiple edits
  input.onblur = null;
  input.onkeydown = null;

  input.onblur = input.onkeydown = (e) => {
    if (e.type === 'blur' || (e.type === 'keydown' && e.key === 'Enter')) {
      const newMsg = input.value.trim();
      if (newMsg && newMsg !== oldMsg) {
        socket.emit('edit_message', { id: msgId, text: newMsg });
      }
      input.replaceWith(document.createTextNode(newMsg || oldMsg));
    }
  };
}

function deleteMessage(msgId) {
  if (confirm('Delete this message?')) {
    socket.emit('delete_message', { id: msgId });
  }
}

function copyText(msg) {
  navigator.clipboard.writeText(msg);
}

// Message grouping
function renderMessages(messageList) {
  messagesDiv.innerHTML = '';
  let lastUser = null;
  let groupDiv = null;
  messageList.forEach((msg, i) => {
    const isSameUser = lastUser && msg.username === lastUser.username && msg.avatar === lastUser.avatar;
    if (!isSameUser) {
      groupDiv = document.createElement('div');
      groupDiv.className = 'chat-message-group fade-in';
      messagesDiv.appendChild(groupDiv);
    }
    const messageDiv = createMessageDiv(msg.username, msg.avatar, msg.text, msg.self, msg.id, msg.timestamp, msg.status);
    if (groupDiv) groupDiv.appendChild(messageDiv);
    lastUser = msg;
  });
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

// Store messages for grouping
let messageHistory = [];

socket.on('message', data => {
  console.log('[DEBUG] Received message:', data);
  const self = data.username === myUsername && data.avatar === myAvatar;

  // Replace the temp message if tempId exists
  if (self && data.tempId) {
    const index = messageHistory.findIndex(m => m.id === data.tempId);
    if (index !== -1) {
      messageHistory[index] = {
        username: data.username,
        avatar: data.avatar,
        text: data.msg,
        self,
        id: data.id,
        timestamp: data.timestamp,
        status: data.status || ''
      };
      renderMessages(messageHistory);
      return;
    }
  }

  // Add message only if not already present
  if (!messageHistory.some(msg => msg.id === data.id)) {
    messageHistory.push({
      username: data.username,
      avatar: data.avatar,
      text: data.msg,
      self,
      id: data.id,
      timestamp: data.timestamp,
      status: data.status || ''
    });
    renderMessages(messageHistory);
  } else {
    console.log('[DEBUG] Duplicate message ignored:', data);
  }
});

socket.on('message_update', data => {
  // Reload channel to update message grouping
  if (currentServer && currentChannel) {
    socket.emit('join_channel', { server: currentServer, channel: currentChannel });
  }
});

socket.on('reactions_update', data => {
  messageReactions[data.message_id] = data.reactions;
  // Re-render messages to update reactions
  renderMessages(messageHistory);
});

// Default emoji options for reactions
const DEFAULT_REACTIONS = ['👍', '😂', '😊', '🔥', '😮', '😢', '🎉', '❤️'];

// Track reactions for each message
let messageReactions = {};

function createReactionsBar(msgId, reactions) {
  const bar = document.createElement('div');
  bar.className = 'reactions-bar';
  // Render each reaction with count and tooltip of users
  Object.entries(reactions || {}).forEach(([emoji, users]) => {
    const btn = document.createElement('button');
    btn.className = 'reaction-btn';
    btn.textContent = `${emoji} ${users.length}`;
    // Tooltip: show usernames/avatars
    btn.title = users.map(u => `${u.avatar} ${u.username}`).join(', ');
    // Highlight if I have reacted
    if (hasReacted(users)) btn.classList.add('selected');
    btn.onclick = () => {
      if (hasReacted(users)) {
        socket.emit('remove_reaction', { message_id: msgId, emoji });
      } else {
        socket.emit('add_reaction', { message_id: msgId, emoji });
      }
    };
    bar.appendChild(btn);
  });
  // Add a + button for new emoji
  const addBtn = document.createElement('button');
  addBtn.className = 'reaction-btn';
  addBtn.textContent = '+';
  addBtn.onclick = () => {
    const emoji = prompt('React with emoji:', '😊');
    if (emoji && emoji.length <= 2) {
      socket.emit('add_reaction', { message_id: msgId, emoji });
    }
  };
  bar.appendChild(addBtn);
  return bar;
}

function hasReacted(users) {
  return users && users.some(u => u.username === myUsername && u.avatar === myAvatar);
}

// Update createMessageDiv to render reactions bar
function createMessageDiv(username, avatar, msg, self = false, msgId = null, timestamp = null, status = '', reactions = []) {
  const div = document.createElement('div');
  div.style.display = 'flex';
  div.style.alignItems = 'center';
  div.style.gap = '0.5rem';
  div.className = 'chat-message fade-in';
  // Status dot
  const { online, last_seen } = getUserStatus(username, avatar);
  const statusDot = document.createElement('span');
  statusDot.style.display = 'inline-block';
  statusDot.style.width = '10px';
  statusDot.style.height = '10px';
  statusDot.style.borderRadius = '50%';
  statusDot.style.marginRight = '0.2em';
  statusDot.style.background = online ? '#43b581' : '#747f8d';
  statusDot.title = online ? 'Online' : (last_seen ? 'Last seen: ' + formatTimestamp(last_seen) : 'Offline');
  div.appendChild(statusDot);
  // Highlight mentions
  const highlightedMsg = highlightMentions(msg);
  div.innerHTML += `<span class="avatar" title="${status}">${avatar}</span> <b${self ? ' style="color:#8be9fd"' : ''} title="${status}">${username}</b>: <span class="msg-text">${highlightedMsg}</span>`;
  if (timestamp) {
    const timeSpan = document.createElement('span');
    timeSpan.style.fontSize = '0.8em';
    timeSpan.style.color = '#aaa';
    timeSpan.style.marginLeft = '0.5em';
    timeSpan.textContent = formatTimestamp(timestamp);
    div.appendChild(timeSpan);
  }
  // Pin/unpin button
  if (msgId) {
    const isPinned = pinnedMessages.some(m => m.id === msgId);
    const pinBtn = document.createElement('button');
    pinBtn.className = 'pin-btn' + (isPinned ? ' pinned' : '');
    pinBtn.title = isPinned ? 'Unpin message' : 'Pin message';
    pinBtn.innerHTML = '📌';
    pinBtn.onclick = () => {
      if (isPinned) {
        socket.emit('unpin_message', { message_id: msgId });
      } else {
        socket.emit('pin_message', { message_id: msgId });
      }
    };
    div.appendChild(pinBtn);
  }
  // Toast notification if this message mentions me (and not my own message)
  if (!self && myUsername && msg.toLowerCase().includes('@' + myUsername.toLowerCase())) {
    showToast(`You were mentioned by ${username}`);
  }
  if (self && msgId) {
    const actions = document.createElement('span');
    actions.className = 'msg-actions';
    actions.style.marginLeft = '0.5em';
    actions.innerHTML = `
      <button class='msg-btn msg-edit' title='Edit'>✏️</button>
      <button class='msg-btn msg-delete' title='Delete'>🗑️</button>
      <button class='msg-btn msg-copy' title='Copy'>📋</button>
      <button class='msg-btn msg-react' title='React'>😊</button>
    `;
    div.appendChild(actions);
    actions.querySelector('.msg-edit').onclick = () => editMessage(msgId, div, msg);
    actions.querySelector('.msg-delete').onclick = () => deleteMessage(msgId);
    actions.querySelector('.msg-copy').onclick = () => copyText(msg);
    actions.querySelector('.msg-react').onclick = () => {
      const emoji = prompt('React with emoji:', '😊');
      if (emoji && emoji.length <= 2) {
        socket.emit('add_reaction', { message_id: msgId, emoji });
      }
    };
  } else if (msgId) {
    const actions = document.createElement('span');
    actions.className = 'msg-actions';
    actions.style.marginLeft = '0.5em';
    actions.innerHTML = `<button class='msg-btn msg-copy' title='Copy'>📋</button>`;
    div.appendChild(actions);
    actions.querySelector('.msg-copy').onclick = () => copyText(msg);
  }
  // Reactions bar
  if (msgId) {
    const reactions = messageReactions[msgId] || {};
    div.appendChild(createReactionsBar(msgId, reactions));
  }
  return div;
}

// Show user avatars in sidebar for each server (if available)
function renderServers(servers) {
  serverSidebar.querySelectorAll('.server:not(.add-server)').forEach(e => e.remove());

  // Remove existing context menu if any
  const existingMenu = document.getElementById('server-context-menu');
  if (existingMenu) {
    existingMenu.remove();
  }

  servers.forEach(server => {
    const div = document.createElement('div');
    div.className = 'server' + (server === currentServer ? ' selected' : '');
    div.setAttribute('data-server-name', server);  // Add this attribute for deletion selector

    // Use the first letter of the server name in uppercase as the avatar
    const avatar = server.charAt(0).toUpperCase();

    // Only show the avatar (first letter) inside the circle icon
    div.innerHTML = `<span class='avatar'>${avatar}</span>`;

    div.title = server;

    div.onclick = () => {
      if (currentServer !== server) {
        currentServer = server;
        currentChannel = null;
        socket.emit('join_server', { server });
        renderServers(servers);
        messageHistory = [];
        messagesDiv.innerHTML = '';
        chatHeader.textContent = 'Select a channel';
        chatForm.style.display = 'none';
        channelList.innerHTML = '';
        userListDiv.innerHTML = '';
      }
    };

    // Add context menu event for right click
    div.addEventListener('contextmenu', (e) => {
      e.preventDefault();
      // Remove any existing context menu
      const oldMenu = document.getElementById('server-context-menu');
      if (oldMenu) oldMenu.remove();

      // Create context menu div
      const menu = document.createElement('div');
      menu.id = 'server-context-menu';
      menu.style.position = 'fixed';
      menu.style.top = `${e.clientY}px`;
      menu.style.left = `${e.clientX}px`;
      menu.style.background = '#2f3136';
      menu.style.border = '1px solid #23272a';
      menu.style.borderRadius = '6px';
      menu.style.padding = '0.5rem 0';
      menu.style.zIndex = '1000';
      menu.style.minWidth = '120px';
      menu.style.color = '#fff';
      menu.style.fontSize = '0.9rem';
      menu.style.boxShadow = '0 2px 10px rgba(0,0,0,0.5)';

      // Add Delete option
      const deleteOption = document.createElement('div');
      deleteOption.textContent = 'Delete Server';
      deleteOption.style.padding = '0.5rem 1rem';
      deleteOption.style.cursor = 'pointer';
      deleteOption.onmouseenter = () => deleteOption.style.background = '#5865f2';
      deleteOption.onmouseleave = () => deleteOption.style.background = 'transparent';
      deleteOption.onclick = () => {
        if (confirm(`Are you sure you want to delete the server "${server}"?`)) {
          socket.emit('delete_server', { server });
          menu.remove();
        }
      };
      menu.appendChild(deleteOption);

      // Append menu to body
      document.body.appendChild(menu);

      // Remove menu on click elsewhere
      const removeMenu = (event) => {
        if (!menu.contains(event.target)) {
          menu.remove();
          document.removeEventListener('click', removeMenu);
        }
      };
      document.addEventListener('click', removeMenu);
    });

    serverSidebar.insertBefore(div, addServerBtn);
  });
}

function formatTimestamp(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  return d.toLocaleString();
}

function escapeHTML(str) {
  return str.replace(/[&<>'"]/g, tag => ({'&':'&amp;','<':'<','>':'>','\'':'&#39;','"':'"'}[tag]));
}

function setTheme(theme) {
  if (theme === 'light') {
    document.body.classList.add('theme-light');
    themeToggle.textContent = '☀️';
  } else {
    document.body.classList.remove('theme-light');
    themeToggle.textContent = '🌙';
  }
  localStorage.setItem('theme', theme);
}

themeToggle.onclick = () => {
  const isLight = document.body.classList.contains('theme-light');
  setTheme(isLight ? 'dark' : 'light');
};

// On load, restore theme
const savedTheme = localStorage.getItem('theme');
setTheme(savedTheme === 'light' ? 'light' : 'dark'); 

socket.on('pinned_messages', data => {
  // Only update if in the current channel
  if (data.server === currentServer && data.channel === currentChannel) {
    pinnedMessages = data.messages;
    renderPinnedBar();
  }
});

function renderPinnedBar() {
  pinnedBar.innerHTML = '';
  if (!pinnedMessages.length) return;
  pinnedMessages.forEach(msg => {
    const div = document.createElement('div');
    div.className = 'pinned-msg';
    div.innerHTML = `<span class='avatar'>${msg.avatar}</span> <b>${msg.username}</b>: <span>${escapeHTML(msg.text)}</span>`;
    if (msg.timestamp) {
      const timeSpan = document.createElement('span');
      timeSpan.style.fontSize = '0.8em';
      timeSpan.style.color = '#aaa';
      timeSpan.style.marginLeft = '0.5em';
      timeSpan.textContent = formatTimestamp(msg.timestamp);
      div.appendChild(timeSpan);
    }
    const unpinBtn = document.createElement('button');
    unpinBtn.className = 'pin-btn pinned';
    unpinBtn.title = 'Unpin message';
    unpinBtn.innerHTML = '📌';
    unpinBtn.onclick = () => socket.emit('unpin_message', { message_id: msg.id });
    div.appendChild(unpinBtn);
    pinnedBar.appendChild(div);
  });
}

