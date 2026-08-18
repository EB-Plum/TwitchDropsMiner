const STYLESHEET_ID = 'progress-health-stylesheet';
const WARNING_ID = 'progress-health-warning';

function ensureStylesheet() {
    if (document.getElementById(STYLESHEET_ID)) return;
    const link = document.createElement('link');
    link.id = STYLESHEET_ID;
    link.rel = 'stylesheet';
    link.href = '/static/progress-health.css';
    document.head.appendChild(link);
}

function ensureWarningElement() {
    let warning = document.getElementById(WARNING_ID);
    if (warning) return warning;

    const progressContainer = document.getElementById('progress-container');
    if (!progressContainer) return null;

    warning = document.createElement('div');
    warning.id = WARNING_ID;
    warning.className = 'progress-health-warning';
    warning.setAttribute('role', 'status');
    warning.setAttribute('aria-live', 'polite');
    warning.hidden = true;

    const alertId = document.createElement('span');
    alertId.className = 'progress-health-warning__id';
    const message = document.createElement('span');
    message.className = 'progress-health-warning__message';
    warning.append(alertId, message);
    progressContainer.parentElement.insertBefore(warning, progressContainer);
    return warning;
}

export function updateProgressHealth(data) {
    ensureStylesheet();
    const warning = ensureWarningElement();
    if (!warning) return;

    if (!data) {
        warning.hidden = true;
        return;
    }

    warning.querySelector('.progress-health-warning__id').textContent = data.id;
    warning.querySelector('.progress-health-warning__message').textContent = data.message;
    warning.title = `Detailed diagnostics are available in logs/TDM.log (${data.id})`;
    warning.hidden = false;
}
