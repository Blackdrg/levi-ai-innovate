// Image generator helper
async function generateImage(quote, author, mood) {
  try {
    const data = await window.api.generateQuoteImage(quote, author, mood);
    const img = new Image();
    img.src = data.image_b64;
    img.className = 'w-full h-48 rounded-xl shadow-2xl mx-auto mt-2';
    const modal = document.createElement('div');
    modal.innerHTML = `<div class="fixed inset-0 bg-black/80 flex items-center justify-center z-50" onclick="this.remove()">
      <div class="max-w-md p-8 glass rounded-2xl text-white text-center" onclick="event.stopPropagation()">
        <img src="${data.image_b64}" alt="Quote image" class="w-full h-64 rounded-xl shadow-2xl mb-4">
        <button onclick="navigator.clipboard.writeText('${quote}'); this.innerHTML = 'Copied!'" class="bg-blue-500 hover:bg-blue-400 p-3 rounded-xl text-white mb-2 w-full">Copy Quote</button>
        <button onclick="this.parentElement.parentElement.remove()" class="bg-gray-500 hover:bg-gray-400 p-3 rounded-xl text-white w-full">Close</button>
      </div>
    </div>`;
    document.body.appendChild(modal.firstElementChild);
  } catch (err) {
    console.error('Image gen error', err);
  }
}

