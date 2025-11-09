/**
 * Character Quick View Popup
 *
 * Provides a floating button that opens a popup with:
 * - Character portrait/name
 * - Quick stats (HP, AC, etc.)
 * - Common actions (attack, skill check, etc.)
 */

class CharacterQuickView {
    constructor(entityId, characterName) {
        this.entityId = entityId;
        this.characterName = characterName;
        this.isOpen = false;
        this.createElements();
        this.attachEventListeners();
    }

    createElements() {
        // Create floating button
        this.button = document.createElement('div');
        this.button.id = 'quick-view-button';
        this.button.innerHTML = '⚔️';
        this.button.style.cssText = `
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            width: 60px;
            height: 60px;
            background: linear-gradient(135deg, #d4af37, #b8942b);
            color: #1a1520;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            cursor: pointer;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
            z-index: 1000;
            transition: all 0.3s;
        `;

        // Create popup
        this.popup = document.createElement('div');
        this.popup.id = 'quick-view-popup';
        this.popup.style.cssText = `
            position: fixed;
            bottom: 6rem;
            right: 2rem;
            width: 350px;
            max-height: 600px;
            overflow-y: auto;
            background: linear-gradient(145deg, #1a1520, #211528);
            border: 2px solid #d4af37;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
            z-index: 999;
            display: none;
            padding: 1.5rem;
        `;

        this.popup.innerHTML = this.buildPopupContent();

        document.body.appendChild(this.button);
        document.body.appendChild(this.popup);
    }

    buildPopupContent() {
        return `
            <div class="quick-view-header" style="margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 2px solid #3d2b4d;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: #d4af37; font-family: 'Cinzel', serif; font-size: 1.3rem;">${this.characterName}</h3>
                    <button onclick="window.characterQuickView.close()" style="background: none; border: none; color: #6a5a7a; font-size: 1.5rem; cursor: pointer; padding: 0; line-height: 1;">×</button>
                </div>
                <div id="quick-stats" style="margin-top: 0.75rem; display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; font-size: 0.9rem;">
                    <div style="text-align: center; padding: 0.5rem; background: rgba(212, 175, 55, 0.1); border-radius: 4px;">
                        <div style="color: #6a5a7a; font-size: 0.75rem;">HP</div>
                        <div style="color: #d4af37; font-weight: bold;" id="quick-hp">-</div>
                    </div>
                    <div style="text-align: center; padding: 0.5rem; background: rgba(212, 175, 55, 0.1); border-radius: 4px;">
                        <div style="color: #6a5a7a; font-size: 0.75rem;">AC</div>
                        <div style="color: #d4af37; font-weight: bold;" id="quick-ac">-</div>
                    </div>
                    <div style="text-align: center; padding: 0.5rem; background: rgba(212, 175, 55, 0.1); border-radius: 4px;">
                        <div style="color: #6a5a7a; font-size: 0.75rem;">PROF</div>
                        <div style="color: #d4af37; font-weight: bold;" id="quick-prof">-</div>
                    </div>
                </div>
            </div>

            <div class="quick-actions" style="display: grid; gap: 0.5rem;">
                <h4 style="margin: 0 0 0.5rem 0; color: #d4af37; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.05em;">Quick Actions</h4>

                <button onclick="window.characterQuickView.rollInitiative()" class="quick-action-btn">
                    🎲 Roll Initiative
                </button>

                <button onclick="window.characterQuickView.rollPerception()" class="quick-action-btn">
                    👁️ Perception Check
                </button>

                <button onclick="window.characterQuickView.rollInvestigation()" class="quick-action-btn">
                    🔍 Investigation Check
                </button>

                <button onclick="window.characterQuickView.rollInsight()" class="quick-action-btn">
                    💭 Insight Check
                </button>

                <button onclick="window.characterQuickView.openInventory()" class="quick-action-btn">
                    🎒 View Inventory
                </button>

                <button onclick="window.characterQuickView.rest()" class="quick-action-btn">
                    😴 Take a Rest
                </button>
            </div>
        `;
    }

    attachEventListeners() {
        this.button.addEventListener('click', () => this.toggle());
        this.button.addEventListener('mouseenter', () => {
            this.button.style.transform = 'scale(1.1)';
            this.button.style.boxShadow = '0 6px 16px rgba(212, 175, 55, 0.4)';
        });
        this.button.addEventListener('mouseleave', () => {
            this.button.style.transform = 'scale(1)';
            this.button.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
        });

        // Add CSS for action buttons
        const style = document.createElement('style');
        style.textContent = `
            .quick-action-btn {
                padding: 0.75rem 1rem;
                background: linear-gradient(135deg, #2d1b3d, #211528);
                color: #f0e6d6;
                border: 1px solid #3d2b4d;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.9rem;
                font-weight: 600;
                text-align: left;
                transition: all 0.2s;
                font-family: inherit;
            }

            .quick-action-btn:hover {
                background: linear-gradient(135deg, #3d2b4d, #2d1b3d);
                border-color: #d4af37;
                transform: translateX(4px);
            }

            .quick-action-btn:active {
                transform: translateX(2px);
            }
        `;
        document.head.appendChild(style);
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        this.isOpen = true;
        this.popup.style.display = 'block';
        this.loadQuickStats();

        // Animate in
        this.popup.style.opacity = '0';
        this.popup.style.transform = 'translateY(20px)';
        setTimeout(() => {
            this.popup.style.transition = 'all 0.3s';
            this.popup.style.opacity = '1';
            this.popup.style.transform = 'translateY(0)';
        }, 10);
    }

    close() {
        this.isOpen = false;
        this.popup.style.opacity = '0';
        this.popup.style.transform = 'translateY(20px)';
        setTimeout(() => {
            this.popup.style.display = 'none';
        }, 300);
    }

    loadQuickStats() {
        // Fetch current character stats
        fetch(`/client/api/entities/${this.entityId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const components = data.entity.components || {};

                    // Health
                    const health = components.Health || {};
                    const currentHp = health.current_hp || 0;
                    const maxHp = health.max_hp || 0;
                    document.getElementById('quick-hp').textContent = `${currentHp}/${maxHp}`;

                    // Armor Class
                    const armor = components.Armor || {};
                    document.getElementById('quick-ac').textContent = armor.armor_class || '-';

                    // Proficiency
                    const attributes = components.Attributes || {};
                    const level = attributes.level || 1;
                    const proficiency = Math.floor((level - 1) / 4) + 2;
                    document.getElementById('quick-prof').textContent = `+${proficiency}`;
                }
            })
            .catch(error => {
                console.error('Failed to load quick stats:', error);
            });
    }

    // Quick Action Methods
    rollInitiative() {
        this.rollDice('1d20+0', 'Initiative', 'dexterity');
    }

    rollPerception() {
        this.rollSkillCheck('wisdom', 'Perception');
    }

    rollInvestigation() {
        this.rollSkillCheck('intelligence', 'Investigation');
    }

    rollInsight() {
        this.rollSkillCheck('wisdom', 'Insight');
    }

    rollSkillCheck(attribute, skillName) {
        // Get the entity's attribute modifier
        fetch(`/client/api/entities/${this.entityId}`)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const attributes = data.entity.components?.Attributes || {};
                    const attrValue = attributes[attribute] || 10;
                    const modifier = Math.floor((attrValue - 10) / 2);
                    const modStr = modifier >= 0 ? `+${modifier}` : `${modifier}`;

                    this.rollDice(`1d20${modStr}`, `${skillName} Check`, attribute);
                }
            })
            .catch(error => {
                console.error('Failed to get attributes:', error);
                this.rollDice('1d20+0', `${skillName} Check`, attribute);
            });
    }

    rollDice(notation, label, context) {
        // If dice roller Alpine component exists, use it
        if (window.Alpine && typeof rollDice === 'function') {
            rollDice(notation, this.entityId, context, label);
        } else {
            alert(`Rolling ${notation} for ${label}...`);
        }
        this.close();
    }

    openInventory() {
        // Scroll to inventory section
        const inventoryDisplay = document.querySelector('[id^="inventory-display-"]');
        if (inventoryDisplay) {
            inventoryDisplay.scrollIntoView({ behavior: 'smooth', block: 'center' });
            this.close();
        } else {
            alert('Inventory not found on this page');
        }
    }

    rest() {
        if (confirm('Take a short rest? (This will restore some HP)')) {
            fetch(`/client/api/entities/${this.entityId}/rest`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rest_type: 'short' })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    alert('You take a short rest and feel refreshed!');
                    location.reload();
                } else {
                    alert('Rest failed: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Rest error:', error);
                alert('Failed to rest');
            });
            this.close();
        }
    }
}

// Initialize quick view when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a character sheet page or DM chat page
    const characterName = document.querySelector('.character-name');

    let entityId = null;
    let displayName = '';

    if (characterName) {
        // Character sheet page: /character/entity_XXXX
        const entityIdMatch = window.location.pathname.match(/\/character\/(entity_[a-z0-9_\-]+)/);
        if (entityIdMatch) {
            entityId = entityIdMatch[1];
            displayName = characterName.textContent;
        }
    } else {
        // DM chat page: /dm/chat/entity_XXXX
        const dmChatMatch = window.location.pathname.match(/\/dm\/chat\/(entity_[a-z0-9_\-]+)/);
        if (dmChatMatch) {
            entityId = dmChatMatch[1];
            // Get character name from the conversation header
            const conversationHeader = document.querySelector('.dm-chat-header p');
            if (conversationHeader) {
                // Extract "Character Name" from "Conversation with Character Name"
                const match = conversationHeader.textContent.match(/Conversation with (.+)/);
                displayName = match ? match[1] : 'Character';
            } else {
                displayName = 'Character';
            }
        }
    }

    if (entityId) {
        window.characterQuickView = new CharacterQuickView(entityId, displayName);
    }
});
