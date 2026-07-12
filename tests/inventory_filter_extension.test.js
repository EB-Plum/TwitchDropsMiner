const test = require('node:test');
const assert = require('node:assert/strict');

const extension = require('../web/static/inventory-filter-extension.js');

test('migrates legacy filter booleans into dropdown modes', () => {
    assert.deepEqual(
        extension.resolveModes({ show_not_linked: true, show_finished: true }),
        { account: 'not_linked', progress: 'finished' }
    );
    assert.deepEqual(
        extension.resolveModes({
            show_not_linked: true,
            show_linked_only: true,
            show_finished: true,
            show_unfinished_only: true
        }),
        { account: 'linked', progress: 'unfinished' }
    );
});

test('stores dropdown modes without removing legacy keys', () => {
    assert.deepEqual(extension.settingsForModes('linked', 'unfinished'), {
        show_not_linked: false,
        show_linked_only: true,
        show_finished: false,
        show_unfinished_only: true
    });
    assert.deepEqual(extension.settingsForModes('not_linked', 'finished'), {
        show_not_linked: true,
        show_linked_only: false,
        show_finished: true,
        show_unfinished_only: false
    });
});

test('applies account and progress dimensions with AND semantics', () => {
    const linkedUnfinished = { linked: true, total_drops: 2, claimed_drops: 1 };
    const linkedFinished = { linked: true, total_drops: 2, claimed_drops: 2 };
    const unlinkedFinished = { linked: false, total_drops: 2, claimed_drops: 2 };
    const filters = { show_linked_only: true, show_unfinished_only: true };

    assert.equal(extension.matches(linkedUnfinished, filters), true);
    assert.equal(extension.matches(linkedFinished, filters), false);
    assert.equal(extension.matches(unlinkedFinished, filters), false);
});

test('falls back to English while allowing native translation keys', () => {
    assert.equal(extension.translationFor('Unknown').progress_unfinished, 'Unfinished');
    assert.equal(
        extension.translationFor('English', { account_linked: 'Connected' }).account_linked,
        'Connected'
    );
});
