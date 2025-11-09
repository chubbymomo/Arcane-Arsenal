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
import logging
from ..base import Module, ComponentTypeDefinition
from src.core.event_bus import Event

from .attributes import AttributesComponent
from .character_details import CharacterDetailsComponent
from .skills import SkillsComponent
from .experience import ExperienceComponent
from .magic import MagicComponent
from .utils import (
    calculate_proficiency_bonus,
    get_spell_slots_for_level,
    should_auto_add_magic
)

logger = logging.getLogger(__name__)


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

        # Non-spellcasters
        classes.register('fighter', 'Fighter - Master of martial combat', {
            'hit_die': 'd10',
            'primary_ability': 'strength',
            'saves': ['strength', 'constitution'],
            'spellcaster': False
        })
        classes.register('rogue', 'Rogue - Expert in stealth and precision', {
            'hit_die': 'd8',
            'primary_ability': 'dexterity',
            'saves': ['dexterity', 'intelligence'],
            'spellcaster': False
        })
        classes.register('barbarian', 'Barbarian - Primal warrior who rages in battle', {
            'hit_die': 'd12',
            'primary_ability': 'strength',
            'saves': ['strength', 'constitution'],
            'spellcaster': False
        })

        # Full spellcasters (INT-based)
        classes.register('wizard', 'Wizard - Scholar of arcane magic', {
            'hit_die': 'd6',
            'primary_ability': 'intelligence',
            'saves': ['intelligence', 'wisdom'],
            'spellcaster': True,
            'spellcasting_ability': 'intelligence',
            'spell_progression': 'full'
        })

        # Full spellcasters (WIS-based)
        classes.register('cleric', 'Cleric - Divine spellcaster and healer', {
            'hit_die': 'd8',
            'primary_ability': 'wisdom',
            'saves': ['wisdom', 'charisma'],
            'spellcaster': True,
            'spellcasting_ability': 'wisdom',
            'spell_progression': 'full'
        })

        # Full spellcasters (CHA-based)
        classes.register('bard', 'Bard - Charismatic performer and magic user', {
            'hit_die': 'd8',
            'primary_ability': 'charisma',
            'saves': ['dexterity', 'charisma'],
            'spellcaster': True,
            'spellcasting_ability': 'charisma',
            'spell_progression': 'full'
        })

        # Half-casters
        classes.register('paladin', 'Paladin - Holy warrior bound by oath', {
            'hit_die': 'd10',
            'primary_ability': 'strength',
            'saves': ['wisdom', 'charisma'],
            'spellcaster': True,
            'spellcasting_ability': 'charisma',
            'spell_progression': 'half'
        })
        classes.register('ranger', 'Ranger - Wilderness warrior and tracker', {
            'hit_die': 'd10',
            'primary_ability': 'dexterity',
            'saves': ['strength', 'dexterity'],
            'spellcaster': True,
            'spellcasting_ability': 'wisdom',
            'spell_progression': 'half'
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

        # === Spells Registry ===
        spells = engine.create_registry('spells', self.name)

        # Cantrips (Level 0)
        spells.register('fire_bolt', 'Fire Bolt - Ranged fire damage cantrip', {
            'level': 0,
            'school': 'evocation',
            'damage': '1d10',
            'damage_type': 'fire',
            'range': '120 feet',
            'components': ['V', 'S']
        })
        spells.register('mage_hand', 'Mage Hand - Conjure spectral hand', {
            'level': 0,
            'school': 'conjuration',
            'range': '30 feet',
            'components': ['V', 'S'],
            'utility': True
        })
        spells.register('prestidigitation', 'Prestidigitation - Minor magical trick', {
            'level': 0,
            'school': 'transmutation',
            'components': ['V', 'S'],
            'utility': True
        })
        spells.register('sacred_flame', 'Sacred Flame - Radiant damage cantrip', {
            'level': 0,
            'school': 'evocation',
            'damage': '1d8',
            'damage_type': 'radiant',
            'range': '60 feet',
            'components': ['V', 'S']
        })

        # Level 1 Spells
        spells.register('magic_missile', 'Magic Missile - Auto-hit force damage', {
            'level': 1,
            'school': 'evocation',
            'damage': '1d4+1',
            'damage_type': 'force',
            'range': '120 feet',
            'components': ['V', 'S']
        })
        spells.register('shield', 'Shield - +5 AC reaction spell', {
            'level': 1,
            'school': 'abjuration',
            'ac_bonus': 5,
            'components': ['V', 'S'],
            'reaction': True
        })
        spells.register('cure_wounds', 'Cure Wounds - Heal HP', {
            'level': 1,
            'school': 'evocation',
            'healing': '1d8',
            'range': 'Touch',
            'components': ['V', 'S']
        })
        spells.register('detect_magic', 'Detect Magic - Sense magic auras', {
            'level': 1,
            'school': 'divination',
            'ritual': True,
            'components': ['V', 'S'],
            'utility': True
        })

        # Level 2 Spells
        spells.register('scorching_ray', 'Scorching Ray - 3 fire rays', {
            'level': 2,
            'school': 'evocation',
            'damage': '2d6',
            'damage_type': 'fire',
            'range': '120 feet',
            'components': ['V', 'S']
        })
        spells.register('misty_step', 'Misty Step - Teleport 30 feet', {
            'level': 2,
            'school': 'conjuration',
            'range': '30 feet',
            'components': ['V'],
            'utility': True,
            'bonus_action': True
        })
        spells.register('hold_person', 'Hold Person - Paralyze humanoid', {
            'level': 2,
            'school': 'enchantment',
            'range': '60 feet',
            'components': ['V', 'S', 'M'],
            'control': True
        })

        # Level 3 Spells
        spells.register('fireball', 'Fireball - 8d6 fire damage in 20ft radius', {
            'level': 3,
            'school': 'evocation',
            'damage': '8d6',
            'damage_type': 'fire',
            'range': '150 feet',
            'area': '20ft radius',
            'components': ['V', 'S', 'M']
        })
        spells.register('counterspell', 'Counterspell - Negate enemy spell', {
            'level': 3,
            'school': 'abjuration',
            'range': '60 feet',
            'components': ['S'],
            'reaction': True
        })
        spells.register('lightning_bolt', 'Lightning Bolt - 8d6 lightning in line', {
            'level': 3,
            'school': 'evocation',
            'damage': '8d6',
            'damage_type': 'lightning',
            'range': '100 feet',
            'area': '100ft line',
            'components': ['V', 'S', 'M']
        })

        # Level 4 Spells
        spells.register('polymorph', 'Polymorph - Transform creature', {
            'level': 4,
            'school': 'transmutation',
            'range': '60 feet',
            'components': ['V', 'S', 'M'],
            'control': True
        })
        spells.register('dimension_door', 'Dimension Door - Teleport 500 feet', {
            'level': 4,
            'school': 'conjuration',
            'range': '500 feet',
            'components': ['V'],
            'utility': True
        })

        # Level 5 Spells
        spells.register('cone_of_cold', 'Cone of Cold - 8d8 cold damage in cone', {
            'level': 5,
            'school': 'evocation',
            'damage': '8d8',
            'damage_type': 'cold',
            'range': '60 feet',
            'area': '60ft cone',
            'components': ['V', 'S', 'M']
        })
        spells.register('wall_of_force', 'Wall of Force - Invisible force barrier', {
            'level': 5,
            'school': 'evocation',
            'range': '120 feet',
            'components': ['V', 'S', 'M'],
            'utility': True
        })

        # Store engine reference for event handlers
        self.engine = engine

        # Subscribe to component events
        engine.event_bus.subscribe('component.added', self.on_component_added)
        engine.event_bus.subscribe('component.updated', self.on_component_updated)

    def on_component_added(self, event: Event) -> None:
        """
        Auto-add Magic and Skills components when CharacterDetails is added.

        If the character's class is a spellcaster, automatically adds Magic component
        with appropriate spell slots. Also ensures Skills component has correct
        proficiency bonus.
        """
        if not hasattr(self, 'engine'):
            return

        component_type = event.data.get('component_type')
        entity_id = event.entity_id

        # Auto-add Magic component for spellcasters
        if component_type == 'CharacterDetails':
            char_details = self.engine.get_component(entity_id, 'CharacterDetails')
            if not char_details:
                return

            class_name = char_details.data.get('character_class')
            level = char_details.data.get('level', 1)

            # Get class metadata
            try:
                classes_registry = self.engine.create_registry('classes', self.name)
                class_data = classes_registry.get(class_name)
                if class_data and should_auto_add_magic(class_name, class_data.get('metadata', {})):
                    # Check if Magic component already exists
                    if not self.engine.get_component(entity_id, 'Magic'):
                        # Get spellcasting info from class
                        class_meta = class_data.get('metadata', {})
                        spell_ability = class_meta.get('spellcasting_ability', 'intelligence')
                        progression = class_meta.get('spell_progression', 'full')

                        # Calculate spell slots
                        spell_slots = get_spell_slots_for_level(level, progression)

                        # Add Magic component
                        self.engine.add_component(entity_id, 'Magic', {
                            'spellcasting_ability': spell_ability,
                            'spell_slots': spell_slots,
                            'known_spells': [],
                            'prepared_spells': [],
                            'cantrips': []
                        })
                        logger.info(f"Auto-added Magic component to {entity_id} ({class_name}, level {level})")
            except Exception as e:
                logger.warning(f"Could not auto-add Magic component: {e}")

            # Auto-add Skills component with correct proficiency bonus if missing
            if not self.engine.get_component(entity_id, 'Skills'):
                prof_bonus = calculate_proficiency_bonus(level)
                try:
                    self.engine.add_component(entity_id, 'Skills', {
                        'proficient_skills': [],
                        'proficiency_bonus': prof_bonus,
                        'expertise_skills': []
                    })
                    logger.info(f"Auto-added Skills component to {entity_id} with +{prof_bonus} proficiency")
                except Exception as e:
                    logger.warning(f"Could not auto-add Skills component: {e}")

            # Auto-populate saving throw proficiencies in Attributes if missing
            try:
                attributes = self.engine.get_component(entity_id, 'Attributes')
                if attributes and not attributes.data.get('saving_throw_proficiencies'):
                    classes_registry = self.engine.create_registry('classes', self.name)
                    class_data = classes_registry.get(class_name)
                    if class_data:
                        class_meta = class_data.get('metadata', {})
                        save_profs = class_meta.get('saves', [])
                        if save_profs:
                            updated_attrs = attributes.data.copy()
                            updated_attrs['saving_throw_proficiencies'] = save_profs
                            self.engine.update_component(entity_id, 'Attributes', updated_attrs)
                            logger.info(f"Auto-populated saving throw proficiencies for {entity_id}: {save_profs}")
            except Exception as e:
                logger.warning(f"Could not auto-populate saving throw proficiencies: {e}")

    def on_component_updated(self, event: Event) -> None:
        """
        Update related components when CharacterDetails level changes.

        Updates proficiency bonus in Skills and spell slots in Magic when level changes.
        """
        if not hasattr(self, 'engine'):
            return

        component_type = event.data.get('component_type')
        entity_id = event.entity_id

        if component_type == 'CharacterDetails':
            char_details = self.engine.get_component(entity_id, 'CharacterDetails')
            if not char_details:
                return

            level = char_details.data.get('level', 1)
            class_name = char_details.data.get('character_class')

            # Update Skills proficiency bonus
            skills = self.engine.get_component(entity_id, 'Skills')
            if skills:
                new_prof_bonus = calculate_proficiency_bonus(level)
                if skills.data.get('proficiency_bonus') != new_prof_bonus:
                    try:
                        updated_skills = skills.data.copy()
                        updated_skills['proficiency_bonus'] = new_prof_bonus
                        self.engine.update_component(entity_id, 'Skills', updated_skills)
                        logger.info(f"Updated proficiency bonus to +{new_prof_bonus} for {entity_id}")
                    except Exception as e:
                        logger.warning(f"Could not update proficiency bonus: {e}")

            # Update Magic spell slots
            magic = self.engine.get_component(entity_id, 'Magic')
            if magic and class_name:
                try:
                    classes_registry = self.engine.create_registry('classes', self.name)
                    class_data = classes_registry.get(class_name)
                    if class_data:
                        class_meta = class_data.get('metadata', {})
                        progression = class_meta.get('spell_progression', 'full')
                        new_slots = get_spell_slots_for_level(level, progression)

                        # Update spell slots while preserving current/prepared spells
                        updated_magic = magic.data.copy()
                        updated_magic['spell_slots'] = new_slots
                        self.engine.update_component(entity_id, 'Magic', updated_magic)
                        logger.info(f"Updated spell slots for {entity_id} (level {level}, {progression} caster)")
                except Exception as e:
                    logger.warning(f"Could not update spell slots: {e}")

    def register_component_types(self) -> List[ComponentTypeDefinition]:
        """Register fantasy character components."""
        return [
            AttributesComponent(),
            CharacterDetailsComponent(),
            SkillsComponent(),
            ExperienceComponent(),
            MagicComponent()
            # Note: Inventory is handled by the 'items' module through
            # entity relationships (owns, equipped), which is the proper ECS way
        ]


# Export
__all__ = [
    'GenericFantasyModule',
    'AttributesComponent',
    'CharacterDetailsComponent',
    'SkillsComponent',
    'ExperienceComponent',
    'MagicComponent'
]
