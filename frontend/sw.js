self.addEventListener('push', event => {
  const options = {
    body: event.data.text(),
    icon: '/icon-192.png',
    badge: '/badge.png',
    actions: [{action: 'share', title: 'Share Quote'}]
  };
  event.waitUntil(self.registration.showNotification('LEVI Daily Quote', options));
});
