// Debounce function to delay form submission
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Submit form on input with debounce
const debouncedSearch = debounce(function(form) {
    form.submit();
}, 300);