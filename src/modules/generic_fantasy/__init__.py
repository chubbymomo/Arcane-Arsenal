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

from typing import List, Optional, Any
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
        return ['core_components', 'generic_combat', 'rng']

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
        # Create empty spell registry - spells are loaded from data files or added by DMs
        # See: data/spells/starter_spells.json for example spell data
        engine.create_registry('spells', self.name)

        # Load starter spells if available
        from pathlib import Path
        from .spell_utils import load_spells_from_file

        # Path: src/modules/generic_fantasy/__init__.py -> project root
        # .parent (1) = src/modules/generic_fantasy
        # .parent (2) = src/modules
        # .parent (3) = src
        # .parent (4) = project root
        starter_spells_path = Path(__file__).parent.parent.parent.parent / 'data' / 'spells' / 'starter_spells.json'
        if starter_spells_path.exists():
            spell_count = load_spells_from_file(engine, str(starter_spells_path), self.name)
            logger.info(f"Loaded {spell_count} starter spells")
        else:
            logger.warning(f"Starter spells file not found at: {starter_spells_path}")

        # Store engine reference for event handlers
        self.engine = engine

        # Subscribe to component events
        engine.event_bus.subscribe('component.added', self.on_component_added)
        engine.event_bus.subscribe('component.updated', self.on_component_updated)

        # Subscribe to character creation events from web layer
        engine.event_bus.subscribe('character.form_submitted', self.on_character_form_submitted)

    def on_character_form_submitted(self, event: Event) -> None:
        """
        Handle character creation form submission from web layer.

        This event handler allows the module to respond to character creation
        without the web layer having any knowledge of this module's existence.

        The web layer publishes a 'character.form_submitted' event with all form
        data, and this module checks if fantasy-specific fields are present and
        adds appropriate components if they are.
        """
        if not hasattr(self, 'engine'):
            return

        entity_id = event.entity_id
        data = event.data

        # Extract fantasy fields from event data
        race = data.get('race')
        character_class = data.get('class')  # Form uses 'class', not 'character_class'
        alignment = data.get('alignment')

        # Convert attributes from strings to integers (form data comes as strings)
        def safe_int(value):
            if value is None or value == '':
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        strength = safe_int(data.get('strength'))
        dexterity = safe_int(data.get('dexterity'))
        constitution = safe_int(data.get('constitution'))
        intelligence = safe_int(data.get('intelligence'))
        wisdom = safe_int(data.get('wisdom'))
        charisma = safe_int(data.get('charisma'))

        # Only proceed if fantasy fields are provided
        has_attributes = any(attr is not None for attr in [
            strength, dexterity, constitution, intelligence, wisdom, charisma
        ])

        if not (has_attributes or race or character_class or alignment):
            # No fantasy fields provided, nothing for this module to do
            return

        logger.info(f"Processing character.form_submitted event for {entity_id}")

        # Use the module's method to add fantasy components
        result = self.add_fantasy_components(
            self.engine, entity_id,
            race=race,
            character_class=character_class,
            alignment=alignment,
            strength=strength,
            dexterity=dexterity,
            constitution=constitution,
            intelligence=intelligence,
            wisdom=wisdom,
            charisma=charisma
        )

        if result.success:
            logger.info(f"Added fantasy components to {entity_id}: {result.data.get('components_added')}")
        else:
            logger.error(f"Failed to add fantasy components to {entity_id}: {result.error}")

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
                logger.warning(f"CharacterDetails component not found for {entity_id} during auto-add")
                return

            class_name = char_details.data.get('character_class')
            level = char_details.data.get('level', 1)
            logger.info(f"Processing CharacterDetails for {entity_id}: class={class_name}, level={level}")

            # Get class metadata
            try:
                classes_registry = self.engine.create_registry('classes', self.name)
                class_data = classes_registry.get(class_name)

                logger.info(f"Registry lookup for '{class_name}': {class_data}")

                if not class_data:
                    logger.warning(f"No class data found for '{class_name}' in registry")
                    return

                # class_data is a dict with 'key', 'description', 'module', 'metadata' keys
                class_meta = class_data.get('metadata', {})
                logger.info(f"Class metadata for '{class_name}': {class_meta}")

                if should_auto_add_magic(class_name, class_meta):
                    logger.info(f"Class '{class_name}' is a spellcaster - checking if Magic component exists")

                    # Check if Magic component already exists
                    if not self.engine.get_component(entity_id, 'Magic'):
                        # Get spellcasting info from class
                        spell_ability = class_meta.get('spellcasting_ability', 'intelligence')
                        progression = class_meta.get('spell_progression', 'full')

                        logger.info(f"Adding Magic component: ability={spell_ability}, progression={progression}")

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
                        logger.info(f"✓ Auto-added Magic component to {entity_id} ({class_name}, level {level})")
                    else:
                        logger.info(f"Magic component already exists for {entity_id}, skipping auto-add")
                else:
                    logger.info(f"Class '{class_name}' is not a spellcaster (spellcaster={class_meta.get('spellcaster', False)})")
            except Exception as e:
                logger.error(f"Error during Magic auto-add for {entity_id}: {e}", exc_info=True)

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

    def add_fantasy_components(self, engine, entity_id: str, race: str = None,
                               character_class: str = None, alignment: str = None,
                               strength: int = None, dexterity: int = None,
                               constitution: int = None, intelligence: int = None,
                               wisdom: int = None, charisma: int = None):
        """
        Add fantasy-specific components to an entity.

        This method encapsulates the module's logic for creating fantasy characters,
        keeping the web layer free from knowledge of Attributes and CharacterDetails structure.

        Args:
            engine: StateEngine instance
            entity_id: ID of entity to add components to
            race: Character race (optional)
            character_class: Character class (optional)
            alignment: Character alignment (optional)
            strength, dexterity, constitution, intelligence, wisdom, charisma: Attribute scores (optional)

        Returns:
            Result object with success status
        """
        from src.core.result import Result

        try:
            components_added = []

            # Add Attributes component if attribute values provided
            attrs = [strength, dexterity, constitution, intelligence, wisdom, charisma]
            has_attributes = any(attr is not None for attr in attrs)

            if has_attributes:
                # Validate all attributes are present and in range
                if any(attr is None or attr < 1 or attr > 20 for attr in attrs):
                    return Result.fail('All attributes must be provided and between 1 and 20')

                result = engine.add_component(entity_id, 'Attributes', {
                    'strength': strength,
                    'dexterity': dexterity,
                    'constitution': constitution,
                    'intelligence': intelligence,
                    'wisdom': wisdom,
                    'charisma': charisma
                })

                if not result.success:
                    return result

                components_added.append('Attributes')

            # Add CharacterDetails if race, class, or alignment provided
            if race or character_class or alignment:
                char_details = {'level': 1}  # Default starting level
                if race:
                    char_details['race'] = race
                if character_class:
                    char_details['character_class'] = character_class
                if alignment:
                    char_details['alignment'] = alignment

                result = engine.add_component(entity_id, 'CharacterDetails', char_details)

                if not result.success:
                    return result

                components_added.append('CharacterDetails')
                # Event system will auto-add Magic and Skills components if spellcaster

            if not components_added:
                return Result.fail('No fantasy components specified')

            return Result.ok(data={'components_added': components_added})

        except Exception as e:
            return Result.fail(f'Failed to add fantasy components: {str(e)}')

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

    def register_blueprint(self) -> Optional[Any]:
        """
        Register Flask blueprint for fantasy character creation API.

        Provides REST API endpoints for fantasy-specific character management:
        - POST /api/fantasy/character/create - Create fantasy character with race/class/attributes
        """
        from .api import generic_fantasy_bp
        return generic_fantasy_bp


# Export
__all__ = [
    'GenericFantasyModule',
    'AttributesComponent',
    'CharacterDetailsComponent',
    'SkillsComponent',
    'ExperienceComponent',
    'MagicComponent'
]
