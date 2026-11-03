(function () {
    'use strict';

    function getCsrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    function isSameOrigin(url) {
        if (!url) return false;
        // Relative URLs (starting with / or relative path without protocol) are same-origin
        if (typeof url === 'string') {
            if (url.startsWith('/') && !url.startsWith('//')) return true;
            if (!url.includes('://') && !url.startsWith('//')) return true;
        }
        try {
            const parsed = new URL(url, window.location.origin);
            return parsed.origin === window.location.origin;
        } catch (e) {
            return false;
        }
    }

    function isMutating(method) {
        const m = (method || 'GET').toUpperCase();
        return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(m);
    }

    // 1. Monkey-patch window.fetch
    const originalFetch = window.fetch;
    if (originalFetch) {
        window.fetch = function (input, init) {
            init = init || {};
            let url = '';
            if (typeof input === 'string') {
                url = input;
            } else if (input && input.url) {
                url = input.url;
            }

            const method = init.method || (input && input.method) || 'GET';
            if (isMutating(method) && isSameOrigin(url)) {
                const token = getCsrfToken();
                if (token) {
                    if (!init.headers) {
                        init.headers = {};
                    }
                    if (init.headers instanceof Headers) {
                        if (!init.headers.has('X-CSRFToken') && !init.headers.has('x-csrftoken')) {
                            init.headers.set('X-CSRFToken', token);
                        }
                    } else if (Array.isArray(init.headers)) {
                        const hasHeader = init.headers.some(h => h[0].toLowerCase() === 'x-csrftoken');
                        if (!hasHeader) {
                            init.headers.push(['X-CSRFToken', token]);
                        }
                    } else if (typeof init.headers === 'object') {
                        if (!init.headers['X-CSRFToken'] && !init.headers['x-csrftoken']) {
                            init.headers['X-CSRFToken'] = token;
                        }
                    }
                }
            }
            return originalFetch.call(this, input, init);
        };
    }

    // 2. Monkey-patch XMLHttpRequest
    const originalOpen = XMLHttpRequest.prototype.open;
    const originalSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function (method, url) {
        this._csrf_method = method;
        this._csrf_url = url;
        return originalOpen.apply(this, arguments);
    };

    XMLHttpRequest.prototype.send = function () {
        if (isMutating(this._csrf_method) && isSameOrigin(this._csrf_url)) {
            const token = getCsrfToken();
            if (token) {
                try {
                    this.setRequestHeader('X-CSRFToken', token);
                } catch (e) {
                    // Ignore if headers cannot be set in current state
                }
            }
        }
        return originalSend.apply(this, arguments);
    };

    // 3. Configure jQuery if available
    if (typeof window.jQuery !== 'undefined' && window.jQuery.ajaxSetup) {
        window.jQuery.ajaxSetup({
            beforeSend: function (xhr, settings) {
                if (isMutating(settings.type) && isSameOrigin(settings.url)) {
                    const token = getCsrfToken();
                    if (token) {
                        xhr.setRequestHeader('X-CSRFToken', token);
                    }
                }
            }
        });
    }
})();
