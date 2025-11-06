"""
Generic Fantasy Module for Arcane Arsenal.

Provides comprehensive fantasy RPG components including:
- Attributes: Core ability scores (STR, DEX, CON, INT, WIS, CHA)
- CharacterDetails: Race, class, background, alignment
- Skills: Proficiency system for skill checks
- Experience: XP tracking and leveling
- Inventory: Item management with weight tracking
- Magic: Spell slots and known spells

This module is designed to be generic enough for most fantasy systems
while being specific enough to be immediately useful. Worlds can customize
via registries (add custom races, classes, skills, etc.).
"""

from typing import List
from ..base import Module, ComponentTypeDefinition

from .attributes import AttributesComponent


class GenericFantasyModule(Module):
    """
    Generic Fantasy module for Arcane Arsenal.

    Provides standard fantasy RPG components that work with most fantasy systems.
    """

    @property
    def name(self) -> str:
        return "generic_fantasy"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def display_name(self) -> str:
        return "Generic Fantasy System"

    @property
    def description(self) -> str:
        return "Core fantasy RPG components: attributes, skills, classes, magic, and character progression"

    def dependencies(self) -> List[str]:
        """Generic fantasy depends on core components and combat systems."""
        return ['core_components', 'fantasy_combat', 'rng']

    def initialize(self, engine) -> None:
        """Initialize registries for character options."""

        # === Races Registry ===
        races = engine.create_registry('races', self.name)
        races.register('human', 'Human - Versatile and adaptable', {
            'size': 'medium',
            'speed': 30,
            'traits': ['Versatile']
        })
        races.register('elf', 'Elf - Graceful and long-lived', {
            'size': 'medium',
            'speed': 30,
            'traits': ['Keen Senses', 'Fey Ancestry']
        })
        races.register('dwarf', 'Dwarf - Sturdy and resilient', {
            'size': 'medium',
            'speed': 25,
            'traits': ['Darkvision', 'Dwarven Resilience']
        })
        races.register('halfling', 'Halfling - Small and lucky', {
            'size': 'small',
            'speed': 25,
            'traits': ['Lucky', 'Brave']
        })
        races.register('orc', 'Orc - Powerful and fierce', {
            'size': 'medium',
            'speed': 30,
            'traits': ['Powerful Build', 'Relentless']
        })
        races.register('dragonborn', 'Dragonborn - Dragon-descended', {
            'size': 'medium',
            'speed': 30,
            'traits': ['Breath Weapon', 'Draconic Ancestry']
        })

        # === Classes Registry ===
        classes = engine.create_registry('classes', self.name)
        classes.register('fighter', 'Fighter - Master of martial combat', {
            'hit_die': 'd10',
            'primary_ability': 'strength',
            'saves': ['strength', 'constitution']
        })
        classes.register('wizard', 'Wizard - Scholar of arcane magic', {
            'hit_die': 'd6',
            'primary_ability': 'intelligence',
            'saves': ['intelligence', 'wisdom']
        })
        classes.register('rogue', 'Rogue - Expert in stealth and precision', {
            'hit_die': 'd8',
            'primary_ability': 'dexterity',
            'saves': ['dexterity', 'intelligence']
        })
        classes.register('cleric', 'Cleric - Divine spellcaster and healer', {
            'hit_die': 'd8',
            'primary_ability': 'wisdom',
            'saves': ['wisdom', 'charisma']
        })
        classes.register('ranger', 'Ranger - Wilderness warrior and tracker', {
            'hit_die': 'd10',
            'primary_ability': 'dexterity',
            'saves': ['strength', 'dexterity']
        })
        classes.register('barbarian', 'Barbarian - Primal warrior who rages in battle', {
            'hit_die': 'd12',
            'primary_ability': 'strength',
            'saves': ['strength', 'constitution']
        })
        classes.register('bard', 'Bard - Charismatic performer and magic user', {
            'hit_die': 'd8',
            'primary_ability': 'charisma',
            'saves': ['dexterity', 'charisma']
        })
        classes.register('paladin', 'Paladin - Holy warrior bound by oath', {
            'hit_die': 'd10',
            'primary_ability': 'strength',
            'saves': ['wisdom', 'charisma']
        })

        # === Skills Registry ===
        skills = engine.create_registry('skill_types', self.name)

        # Strength-based skills
        skills.register('athletics', 'Athletics - Climbing, jumping, swimming (STR)', {
            'ability': 'strength',
            'category': 'physical'
        })

        # Dexterity-based skills
        skills.register('acrobatics', 'Acrobatics - Balance, tumbling, agility (DEX)', {
            'ability': 'dexterity',
            'category': 'physical'
        })
        skills.register('sleight_of_hand', 'Sleight of Hand - Pickpocketing, lockpicking (DEX)', {
            'ability': 'dexterity',
            'category': 'physical'
        })
        skills.register('stealth', 'Stealth - Hiding, moving silently (DEX)', {
            'ability': 'dexterity',
            'category': 'physical'
        })

        # Intelligence-based skills
        skills.register('arcana', 'Arcana - Magic knowledge and lore (INT)', {
            'ability': 'intelligence',
            'category': 'knowledge'
        })
        skills.register('history', 'History - Historical knowledge (INT)', {
            'ability': 'intelligence',
            'category': 'knowledge'
        })
        skills.register('investigation', 'Investigation - Finding clues, research (INT)', {
            'ability': 'intelligence',
            'category': 'knowledge'
        })
        skills.register('nature', 'Nature - Natural world knowledge (INT)', {
            'ability': 'intelligence',
            'category': 'knowledge'
        })
        skills.register('religion', 'Religion - Religious knowledge (INT)', {
            'ability': 'intelligence',
            'category': 'knowledge'
        })

        # Wisdom-based skills
        skills.register('animal_handling', 'Animal Handling - Calming, training animals (WIS)', {
            'ability': 'wisdom',
            'category': 'perception'
        })
        skills.register('insight', 'Insight - Reading intentions, detecting lies (WIS)', {
            'ability': 'wisdom',
            'category': 'perception'
        })
        skills.register('medicine', 'Medicine - Healing, diagnosing illness (WIS)', {
            'ability': 'wisdom',
            'category': 'perception'
        })
        skills.register('perception', 'Perception - Noticing details, awareness (WIS)', {
            'ability': 'wisdom',
            'category': 'perception'
        })
        skills.register('survival', 'Survival - Tracking, foraging, navigation (WIS)', {
            'ability': 'wisdom',
            'category': 'perception'
        })

        # Charisma-based skills
        skills.register('deception', 'Deception - Lying convincingly (CHA)', {
            'ability': 'charisma',
            'category': 'social'
        })
        skills.register('intimidation', 'Intimidation - Threatening, coercing (CHA)', {
            'ability': 'charisma',
            'category': 'social'
        })
        skills.register('performance', 'Performance - Entertaining, acting (CHA)', {
            'ability': 'charisma',
            'category': 'social'
        })
        skills.register('persuasion', 'Persuasion - Influencing, negotiating (CHA)', {
            'ability': 'charisma',
            'category': 'social'
        })

        # === Alignments Registry ===
        alignments = engine.create_registry('alignments', self.name)
        alignments.register('lawful_good', 'Lawful Good - Honorable and compassionate')
        alignments.register('neutral_good', 'Neutral Good - Kind and helpful')
        alignments.register('chaotic_good', 'Chaotic Good - Free-spirited and benevolent')
        alignments.register('lawful_neutral', 'Lawful Neutral - Orderly and fair')
        alignments.register('true_neutral', 'True Neutral - Balanced and impartial')
        alignments.register('chaotic_neutral', 'Chaotic Neutral - Independent and unpredictable')
        alignments.register('lawful_evil', 'Lawful Evil - Tyrannical and methodical')
        alignments.register('neutral_evil', 'Neutral Evil - Selfish and cruel')
        alignments.register('chaotic_evil', 'Chaotic Evil - Destructive and savage')

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """Register fantasy character components."""
        return [
            AttributesComponent(),
            # TODO: Add other components as they're implemented
            # CharacterDetailsComponent(),
            # SkillsComponent(),
            # ExperienceComponent(),
            # InventoryComponent(),
            # MagicComponent()
        ]


# Export
__all__ = [
    'GenericFantasyModule',
    'AttributesComponent'
]
