(function (root, factory) {
    const extension = factory(root);

    if (typeof module === 'object' && module.exports) {
        module.exports = extension;
    }
    root.InventoryFilterExtension = extension;
}(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
    'use strict';

    const ACCOUNT = Object.freeze({ ALL: 'all', LINKED: 'linked', NOT_LINKED: 'not_linked' });
    const PROGRESS = Object.freeze({ ALL: 'all', FINISHED: 'finished', UNFINISHED: 'unfinished' });

    const TRANSLATIONS = Object.freeze({
        English: ['Account', 'All', 'Linked', 'Not Linked', 'Progress', 'All', 'Finished', 'Unfinished'],
        Dansk: ['Konto', 'Alle', 'Tilknyttet', 'Ikke forbundet', 'Fremskridt', 'Alle', 'Færdig', 'Ikke færdig'],
        Deutsch: ['Konto', 'Alle', 'Verknüpft', 'Nicht Verbunden', 'Fortschritt', 'Alle', 'Abgeschlossen', 'Nicht abgeschlossen'],
        Español: ['Cuenta', 'Todo', 'Vinculado', 'No Vinculado', 'Progreso', 'Todo', 'Terminado', 'Incompleto'],
        Français: ['Compte', 'Tout', 'Lié', 'Non lié', 'Progrès', 'Tout', 'Terminé', 'Non terminé'],
        Indonesian: ['Akun', 'Semua', 'Terhubung', 'Tidak Terhubung', 'Kemajuan', 'Semua', 'Selesai', 'Belum Selesai'],
        Italiano: ['Account', 'Tutto', 'Collegato', 'Non Collegato', 'Progresso', 'Tutto', 'Completato', 'Non completato'],
        Nederlandse: ['Account', 'Alle', 'Gekoppeld', 'Niet gekoppeld', 'Voortgang', 'Alle', 'Voltooid', 'Niet voltooid'],
        Polski: ['Konto', 'Wszystko', 'Połączone', 'Niepołączone', 'Postęp', 'Wszystko', 'Zakończone', 'Niezakończone'],
        Português: ['Conta', 'Tudo', 'Vinculado', 'Não Vinculado', 'Progresso', 'Tudo', 'Concluído', 'Não concluído'],
        Română: ['Cont', 'Toate', 'Conectat', 'Neconectat', 'Progres', 'Toate', 'Terminat', 'Neterminat'],
        Türkçe: ['Hesap', 'Tümü', 'Bağlı', 'Bağlı Değil', 'İlerleme', 'Tümü', 'Tamamlandı', 'Tamamlanmadı'],
        Čeština: ['Účet', 'Vše', 'Propojené', 'Nepřipojeno', 'Průběh', 'Vše', 'Dokončeno', 'Nedokončeno'],
        Русский: ['Аккаунт', 'Все', 'Привязан', 'Не связаны', 'Прогресс', 'Все', 'Завершено', 'Не завершено'],
        Українська: ['Обліковий запис', 'Всі', "Прив'язано", "Не пов'язані", 'Прогрес', 'Всі', 'Завершено', 'Не завершено'],
        العربية: ['حساب', 'الكل', 'مرتبط', 'غير مرتبط', 'تقدم', 'الكل', 'مكتمل', 'غير مكتمل'],
        日本語: ['アカウント', 'すべて', 'リンク済み', '未連携', '進捗', 'すべて', '完了', '未完了'],
        简体中文: ['账户', '全部', '已关联', '未关联', '进度', '全部', '已完成', '未完成'],
        繁體中文: ['帳戶', '全部', '已連結', '未連結', '進度', '全部', '已完成', '未完成']
    });

    const elements = {
        accountLabel: null,
        accountSelect: null,
        progressLabel: null,
        progressSelect: null
    };

    function resolveModes(filters = {}) {
        const account = filters.show_linked_only
            ? ACCOUNT.LINKED
            : filters.show_not_linked ? ACCOUNT.NOT_LINKED : ACCOUNT.ALL;
        const progress = filters.show_unfinished_only
            ? PROGRESS.UNFINISHED
            : filters.show_finished ? PROGRESS.FINISHED : PROGRESS.ALL;
        return { account, progress };
    }

    function settingsForModes(account = ACCOUNT.ALL, progress = PROGRESS.ALL) {
        const safeAccount = Object.values(ACCOUNT).includes(account) ? account : ACCOUNT.ALL;
        const safeProgress = Object.values(PROGRESS).includes(progress) ? progress : PROGRESS.ALL;
        return {
            show_not_linked: safeAccount === ACCOUNT.NOT_LINKED,
            show_linked_only: safeAccount === ACCOUNT.LINKED,
            show_finished: safeProgress === PROGRESS.FINISHED,
            show_unfinished_only: safeProgress === PROGRESS.UNFINISHED
        };
    }

    function matches(campaign, filters, isFinished) {
        const { account, progress } = resolveModes(filters);
        const finished = isFinished ?? (
            campaign.total_drops > 0 && campaign.claimed_drops === campaign.total_drops
        );

        if (account === ACCOUNT.LINKED && !campaign.linked) return false;
        if (account === ACCOUNT.NOT_LINKED && campaign.linked) return false;
        if (progress === PROGRESS.FINISHED && !finished) return false;
        if (progress === PROGRESS.UNFINISHED && finished) return false;
        return true;
    }

    function translationFor(languageName, nativeFilters = {}) {
        const values = TRANSLATIONS[languageName] || TRANSLATIONS.English;
        return {
            account: nativeFilters.account || values[0],
            account_all: nativeFilters.account_all || values[1],
            account_linked: nativeFilters.account_linked || values[2],
            account_not_linked: nativeFilters.account_not_linked || values[3],
            progress: nativeFilters.progress || values[4],
            progress_all: nativeFilters.progress_all || values[5],
            progress_finished: nativeFilters.progress_finished || values[6],
            progress_unfinished: nativeFilters.progress_unfinished || values[7]
        };
    }

    function createOption(value, text) {
        const option = document.createElement('option');
        option.value = value;
        option.textContent = text;
        return option;
    }

    function createField(labelText, selectId, options) {
        const label = document.createElement('label');
        label.className = 'inventory-filter-extension__field';

        const labelTextElement = document.createElement('span');
        labelTextElement.textContent = labelText;

        const select = document.createElement('select');
        select.id = selectId;
        for (const [value, text] of options) {
            select.appendChild(createOption(value, text));
        }

        label.append(labelTextElement, select);
        return { label, labelTextElement, select };
    }

    function syncLegacyControls(settings) {
        const notLinked = document.getElementById('filter-not-linked');
        const finished = document.getElementById('filter-finished');
        if (notLinked) notLinked.checked = settings.show_not_linked;
        if (finished) finished.checked = settings.show_finished;
    }

    function getAdditionalSettings() {
        const settings = settingsForModes(
            elements.accountSelect?.value,
            elements.progressSelect?.value
        );
        syncLegacyControls(settings);
        return {
            show_linked_only: settings.show_linked_only,
            show_unfinished_only: settings.show_unfinished_only
        };
    }

    function restore(filters) {
        const modes = resolveModes(filters);
        if (elements.accountSelect) elements.accountSelect.value = modes.account;
        if (elements.progressSelect) elements.progressSelect.value = modes.progress;
        syncLegacyControls(settingsForModes(modes.account, modes.progress));
    }

    function reset() {
        if (elements.accountSelect) elements.accountSelect.value = ACCOUNT.ALL;
        if (elements.progressSelect) elements.progressSelect.value = PROGRESS.ALL;
        syncLegacyControls(settingsForModes());
    }

    function translate(translations) {
        if (!elements.accountSelect || !elements.progressSelect) return;
        const nativeFilters = translations?.gui?.inventory?.filters || {};
        const text = translationFor(translations?.language_name, nativeFilters);

        elements.accountLabel.textContent = text.account;
        elements.accountSelect.options[0].textContent = text.account_all;
        elements.accountSelect.options[1].textContent = text.account_linked;
        elements.accountSelect.options[2].textContent = text.account_not_linked;
        elements.progressLabel.textContent = text.progress;
        elements.progressSelect.options[0].textContent = text.progress_all;
        elements.progressSelect.options[1].textContent = text.progress_finished;
        elements.progressSelect.options[2].textContent = text.progress_unfinished;
    }

    function init() {
        const checkboxGroup = document.querySelector('.inventory-filters .filter-checkboxes');
        if (!checkboxGroup || elements.accountSelect) return;

        const text = translationFor('English');
        const accountField = createField(text.account, 'filter-account-link', [
            [ACCOUNT.ALL, text.account_all],
            [ACCOUNT.LINKED, text.account_linked],
            [ACCOUNT.NOT_LINKED, text.account_not_linked]
        ]);
        const progressField = createField(text.progress, 'filter-progress', [
            [PROGRESS.ALL, text.progress_all],
            [PROGRESS.FINISHED, text.progress_finished],
            [PROGRESS.UNFINISHED, text.progress_unfinished]
        ]);

        const container = document.createElement('div');
        container.className = 'inventory-filter-extension';
        container.append(accountField.label, progressField.label);
        checkboxGroup.parentElement.insertBefore(container, checkboxGroup);

        elements.accountLabel = accountField.labelTextElement;
        elements.accountSelect = accountField.select;
        elements.progressLabel = progressField.labelTextElement;
        elements.progressSelect = progressField.select;

        for (const id of ['filter-not-linked', 'filter-finished']) {
            document.getElementById(id)?.closest('label')
                ?.classList.add('inventory-filter-extension__legacy-control');
        }

        const handleChange = () => {
            getAdditionalSettings();
            if (typeof root.onInventoryFilterChange === 'function') {
                root.onInventoryFilterChange();
            }
        };
        elements.accountSelect.addEventListener('change', handleChange);
        elements.progressSelect.addEventListener('change', handleChange);
    }

    if (typeof document !== 'undefined') {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
        } else {
            init();
        }
    }

    return {
        ACCOUNT,
        PROGRESS,
        getAdditionalSettings,
        matches,
        reset,
        resolveModes,
        restore,
        settingsForModes,
        translate,
        translationFor
    };
}));
