// JavaScript for frontend logic
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('chat-form');
    const input = document.getElementById('user-input');
    const history = document.getElementById('chat-history');
    const categoryBtns = document.querySelectorAll('.category-btn');
    
    let selectedCategory = 'Medical Support';  // Default
    
    // Category selection
    categoryBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            categoryBtns.forEach(b => b.classList.remove('selected'));
            btn.classList.add('selected');
            selectedCategory = btn.dataset.category;
        });
    });
    
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = input.value.trim();
        if (!query) return;
        
        // Add user message
        addMessage('user', `${selectedCategory}: ${query}`);
        input.value = '';
        
        // Send to backend
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: `query=${encodeURIComponent(query)}&category=${encodeURIComponent(selectedCategory)}`
            });
            const data = await response.json();
            
            if (data.error) {
                addMessage('ai', `Error: ${data.error}`);
            } else {
                typeMessage(data.response);
            }
        } catch (error) {
            addMessage('ai', 'Error: Could not connect to server.');
        }
    });
    
    function addMessage(type, text) {
        const div = document.createElement('div');
        div.classList.add('message', type === 'user' ? 'user-message' : 'ai-message');
        div.textContent = text;
        history.appendChild(div);
        history.scrollTop = history.scrollHeight;
    }
    
    function typeMessage(text) {
        const div = document.createElement('div');
        div.classList.add('message', 'ai-message');
        history.appendChild(div);
        history.scrollTop = history.scrollHeight;
        
        let i = 0;
        const interval = setInterval(() => {
            if (i < text.length) {
                div.textContent += text.charAt(i);
                i++;
            } else {
                clearInterval(interval);
            }
        }, 20);  // Typing speed
    }
});