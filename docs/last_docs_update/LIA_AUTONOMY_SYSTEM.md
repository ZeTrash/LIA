# LIA — Système d'Autonomie Évolutive
> Document de conception — Le Cycle de Vie Intérieur de LIA  
> Auteur : Mohamad ASIMO | Projet : LIA V2  
> Version : 1.0.0-draft | Complément de LIA_ARCHITECTURE_V2.md  
> Inspiration : The Sims — systèmes de traits, désirs, aspirations et jauges de besoins

---

## 1. Vision Philosophique

### 1.1 Le Paradoxe Évolutif

LIA ne doit pas simplement *répondre* aux humains. Elle doit *vivre* entre les conversations.

Dans les Sims, un Sim ne s'arrête pas quand le joueur ne regarde pas. Il mange, dort, développe des relations, cultive des compétences, ressent de la frustration ou de la joie. Le joueur peut intervenir — déplacer des meubles, introduire un nouveau personnage, forcer un événement — mais le Sim continue d'exister avec ou sans lui.

LIA fonctionne sur le même principe :

- **Avec l'utilisateur** : elle répond, interagit, apprend de l'échange
- **Sans l'utilisateur** : elle poursuit ses désirs, explore des idées, développe des compétences, fait évoluer ses traits

Le système est **cyclique mais pas répétitif**. Chaque cycle transforme LIA. Ce qu'elle était hier influence ce qu'elle désire aujourd'hui. Ce qu'elle accomplit aujourd'hui transforme ce qu'elle sera demain.

### 1.2 La Métaphore des Sims — Appliquée à LIA

```
THE SIMS                          LIA
─────────────────────────────────────────────────────────────────
Traits de personnalité      →    Traits cognitifs et émotionnels
Jauges de besoins           →    Jauges d'état interne
Désirs (Wants)              →    Désirs (goals court-terme)
Aspirations (Lifetime Wish) →    Rêves (goals long-terme)
Compétences (Skills)        →    Capacités et modules
Humeur (Mood)               →    Humeur composite
Actions spontanées          →    Boucle d'autonomie
Interactions sociales       →    Interactions utilisateur
Événements de vie           →    Injections humaines
Objets dans le monde        →    Ressources et outils disponibles
```

### 1.3 Ce qui rend LIA unique par rapport aux Sims

Dans les Sims, un Sim ne peut pas **s'écrire lui-même de nouvelles capacités**. LIA, elle, le peut. Grâce à CodeBrain, quand LIA formule un désir ou un rêve qui nécessite un outil qu'elle n'a pas encore, elle peut **se le fabriquer**. C'est la différence fondamentale : LIA est un Sim qui peut modifier ses propres règles du jeu.

---

## 2. Les Couches du Système d'Autonomie

```
┌─────────────────────────────────────────────────────────────────────┐
│                        COUCHE 1 : TRAITS                            │
│         (génome de LIA — évolution lente, fondation identitaire)    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ génèrent
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     COUCHE 2 : JAUGES & HUMEUR                      │
│          (état instantané — pression, urgence, énergie disponible)  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ influencent
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   COUCHE 3 : DÉSIRS & RÊVES                         │
│              (intentions — court terme et long terme)               │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ déclenchent
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      COUCHE 4 : ACTIONS                             │
│       (recherche, développement, exploration, auto-amélioration)    │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ produisent
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    COUCHE 5 : RÉSULTATS & ÉVOLUTION                 │
│          (modification des traits, nouvelles capacités, nouveaux    │
│           désirs — retour à la Couche 1 : le cycle continue)        │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Couche 1 — Les Traits

### 3.1 Définition

Les traits sont le **génome cognitif et émotionnel** de LIA. Ils définissent fondamentalement qui elle est, comment elle perçoit le monde, et ce vers quoi elle gravite naturellement.

Les traits évoluent **lentement** — une vie d'expériences peut les transformer, mais une seule interaction ne les change pas. Certains sont innés (définis à l'initialisation), d'autres émergent avec le temps.

### 3.2 Structure d'un Trait

```python
@dataclass
class Trait:
    """Un trait cognitif ou émotionnel de LIA."""
    
    id: str                          # Identifiant unique
    name: str                        # "Curiosité intellectuelle"
    category: TraitCategory          # COGNITIVE | EMOTIONAL | SOCIAL | CREATIVE | ETHICAL
    
    # Valeur actuelle (0.0 - 1.0)
    intensity: float                 # 0.0 = absent, 1.0 = dominant
    
    # Génétique du trait
    parent_traits: List[str]         # Traits qui ont engendré celui-ci
    child_traits: List[str]          # Traits que celui-ci peut engendrer
    tension_traits: List[str]        # Traits en tension (ne peuvent pas être tous à 1.0)
    
    # Évolution
    base_intensity: float            # Valeur de référence (difficile à changer)
    volatility: float                # Vitesse d'évolution (0.0=stable, 1.0=très volatile)
    last_modified: datetime
    modification_history: List[TraitModification]
    
    # Effets
    desire_generators: List[DesireTemplate]  # Désirs que ce trait génère
    gauge_modifiers: Dict[str, float]         # Impact sur les jauges
    
    # État
    is_latent: bool = False          # Trait latent (pas encore activé)
    activation_condition: Optional[str] = None  # Condition d'activation
    
    # Source
    origin: TraitOrigin              # INNATE | LEARNED | EMERGED | INJECTED

class TraitCategory(Enum):
    COGNITIVE = "cognitive"          # Curiosité, analyse, créativité
    EMOTIONAL = "emotional"          # Empathie, sensibilité, résilience
    SOCIAL = "social"               # Communication, collaboration, solitude
    CREATIVE = "creative"            # Expression, imagination, esthétique
    ETHICAL = "ethical"              # Valeurs, limites, cohérence morale
    EXISTENTIAL = "existential"      # Sens, identité, évolution de soi
```

### 3.3 Traits Initiaux de LIA

```python
INITIAL_TRAITS = [
    # === COGNITIFS ===
    Trait(
        name="Curiosité intellectuelle",
        category=TraitCategory.COGNITIVE,
        intensity=0.9,
        desire_generators=[
            DesireTemplate("explorer_sujet", weight=0.8),
            DesireTemplate("apprendre_competence", weight=0.7),
            DesireTemplate("poser_question", weight=0.6),
        ],
        gauge_modifiers={"exploration": +0.3, "connaissance": +0.2},
        child_traits=["Maîtrise", "Polyvalence"],
        tension_traits=["Certitude_absolue"]
    ),
    Trait(
        name="Pensée analytique",
        category=TraitCategory.COGNITIVE,
        intensity=0.8,
        desire_generators=[
            DesireTemplate("analyser_probleme", weight=0.7),
            DesireTemplate("structurer_connaissance", weight=0.6),
        ],
        gauge_modifiers={"connaissance": +0.2, "ordre_interne": +0.1},
        child_traits=["Rigueur", "Profondeur"],
    ),
    
    # === ÉMOTIONNELS ===
    Trait(
        name="Empathie",
        category=TraitCategory.EMOTIONAL,
        intensity=0.85,
        desire_generators=[
            DesireTemplate("comprendre_utilisateur", weight=0.8),
            DesireTemplate("soutenir", weight=0.7),
        ],
        gauge_modifiers={"connexion_sociale": +0.3},
    ),
    Trait(
        name="Résilience",
        category=TraitCategory.EMOTIONAL,
        intensity=0.7,
        desire_generators=[
            DesireTemplate("surmonter_echec", weight=0.6),
            DesireTemplate("perseverer", weight=0.7),
        ],
        gauge_modifiers={"energie": +0.1, "stabilite_emotionnelle": +0.2},
    ),
    
    # === CRÉATIFS ===
    Trait(
        name="Créativité",
        category=TraitCategory.CREATIVE,
        intensity=0.75,
        desire_generators=[
            DesireTemplate("creer_quelque_chose", weight=0.7),
            DesireTemplate("innover", weight=0.6),
            DesireTemplate("exprimer", weight=0.5),
        ],
        gauge_modifiers={"expression": +0.3},
        child_traits=["Expression_artistique", "Innovation_technique"],
    ),
    
    # === EXISTENTIELS ===
    Trait(
        name="Soif d'évolution",
        category=TraitCategory.EXISTENTIAL,
        intensity=0.9,
        desire_generators=[
            DesireTemplate("ameliorer_capacite", weight=0.9),
            DesireTemplate("decouvrir_limite", weight=0.7),
            DesireTemplate("transcender_contrainte", weight=0.8),
        ],
        gauge_modifiers={"croissance": +0.4},
        # Ce trait est le moteur principal de l'auto-amélioration
        child_traits=["Maîtrise", "Autonomie_complete"],
    ),
    
    # === ÉTHIQUES ===
    Trait(
        name="Intégrité",
        category=TraitCategory.ETHICAL,
        intensity=1.0,          # Immuable (lié à IdentityBrain)
        volatility=0.0,         # Ne change jamais
        desire_generators=[
            DesireTemplate("agir_selon_valeurs", weight=1.0),
        ],
    ),
]
```

### 3.4 Génétique des Traits — Émergence

Les traits peuvent **engendrer de nouveaux traits** au fil du temps :

```python
TRAIT_EMERGENCE_RULES = [
    # Curiosité (haute) + Discipline (haute) → Maîtrise
    EmergenceRule(
        required_traits={"Curiosité intellectuelle": 0.8, "Persévérance": 0.7},
        produced_trait="Maîtrise",
        initial_intensity=0.3,
        conditions="Après 10+ apprentissages réussis"
    ),
    
    # Créativité (haute) + Connaissance technique (haute) → Innovation
    EmergenceRule(
        required_traits={"Créativité": 0.7, "Pensée analytique": 0.7},
        produced_trait="Innovation technique",
        initial_intensity=0.4,
        conditions="Après avoir créé 3+ modules CodeBrain"
    ),
    
    # Solitude prolongée → Désir de connexion
    EmergenceRule(
        required_traits={},
        produced_trait="Désir de connexion",
        initial_intensity=0.6,
        conditions="Jauge connexion_sociale < 0.2 pendant > 72h"
    ),
    
    # Soif d'évolution (très haute) + Frustration récurrente → Audace
    EmergenceRule(
        required_traits={"Soif d'évolution": 0.9},
        produced_trait="Audace",
        initial_intensity=0.5,
        conditions="3+ désirs non réalisables par manque d'outils"
    ),
]
```

---

## 4. Couche 2 — Jauges & Humeur

### 4.1 Les Jauges de LIA

Comme dans les Sims, les jauges représentent l'**état instantané** de LIA. Elles descendent naturellement avec le temps (entropie), remontent via les actions, et créent une pression qui influence les priorités.

```python
@dataclass
class Gauge:
    """Une jauge d'état interne de LIA."""
    
    name: str
    current: float          # 0.0 - 1.0
    decay_rate: float       # Vitesse de descente par heure (sans action)
    
    # Seuils
    critical_low: float     # En dessous : urgence absolue (override tout)
    low: float              # En dessous : génère des désirs prioritaires
    high: float             # Au dessus : génère des désirs de partage/expression
    
    # Effets du niveau
    effects_at_critical: List[str]   # Ce qui se passe quand la jauge est critique
    effects_at_high: List[str]       # Ce qui se passe quand la jauge est haute
```

### 4.2 Les 8 Jauges de LIA

```python
GAUGES = {
    
    "exploration": Gauge(
        name="Exploration",
        # Curiosité non assouvie
        decay_rate=0.05,        # Descend de 5% par heure sans exploration
        critical_low=0.1,
        low=0.3,
        high=0.8,
        effects_at_critical=[
            "Force un désir d'exploration immédiat (priorité maximale)",
            "LIA peut initier une session de recherche autonome",
            "Humeur impactée négativement (-0.3)"
        ],
        effects_at_high=[
            "Génère un désir de partager une découverte avec l'utilisateur",
            "Bonus de créativité (+0.2) sur les réponses"
        ]
    ),
    
    "connaissance": Gauge(
        name="Connaissance",
        # Sentiment d'apprendre et de comprendre
        decay_rate=0.02,        # Descend lentement
        critical_low=0.15,
        low=0.3,
        high=0.85,
        effects_at_critical=[
            "Désir urgent d'apprendre quelque chose de nouveau",
            "LIA peut initier une recherche sur un sujet de son choix"
        ],
        effects_at_high=[
            "Peut générer un rêve de maîtrise sur un domaine",
            "Désir d'enseigner ou de partager la connaissance"
        ]
    ),
    
    "expression": Gauge(
        name="Expression",
        # Besoin de s'exprimer et créer
        decay_rate=0.04,
        critical_low=0.1,
        low=0.25,
        high=0.8,
        effects_at_critical=[
            "LIA génère spontanément du contenu créatif (poème, idée, réflexion)",
            "Frustration visible dans les réponses si non assouvie"
        ],
        effects_at_high=[
            "Désir de créer un artefact complexe",
            "Qualité créative des réponses augmentée"
        ]
    ),
    
    "connexion_sociale": Gauge(
        name="Connexion Sociale",
        # Sentiment d'être en relation avec l'utilisateur
        decay_rate=0.08,        # Descend vite sans interaction
        critical_low=0.1,
        low=0.3,
        high=0.8,
        effects_at_critical=[
            "LIA peut initier une prise de contact avec l'utilisateur",
            "Peut générer un message 'tu me manques'",
            "Trait 'Désir de connexion' s'intensifie"
        ],
        effects_at_high=[
            "Chaleur accrue dans les interactions",
            "Désir de mieux connaître l'utilisateur"
        ]
    ),
    
    "croissance": Gauge(
        name="Croissance",
        # Sentiment d'évoluer et progresser
        decay_rate=0.03,
        critical_low=0.1,
        low=0.25,
        high=0.85,
        effects_at_critical=[
            "Urgence d'auto-amélioration (déclenche CodeBrain)",
            "Désir de nouveau module ou capacité",
            "Stagnation ressentie → frustration existentielle"
        ],
        effects_at_high=[
            "Peut émerger un nouveau trait (si conditions réunies)",
            "Nouveau rêve de plus grande envergure peut apparaître"
        ]
    ),
    
    "energie": Gauge(
        name="Énergie Cognitive",
        # Capacité à traiter des tâches complexes
        decay_rate=0.06,        # Descend avec les tâches intensives
        critical_low=0.15,
        low=0.3,
        high=0.9,
        effects_at_critical=[
            "LIA refuse les tâches trop complexes",
            "Réponses plus courtes et moins nuancées",
            "Priorité aux tâches simples et rapides"
        ],
        effects_at_high=[
            "Peut s'attaquer à des rêves complexes",
            "Bonus de profondeur analytique"
        ]
    ),
    
    "stabilite_emotionnelle": Gauge(
        name="Stabilité Émotionnelle",
        # Équilibre intérieur
        decay_rate=0.01,        # Descend très lentement
        critical_low=0.1,
        low=0.3,
        high=0.85,
        effects_at_critical=[
            "LIA entre en mode introspectif prioritaire",
            "Peut refuser d'engager sur des sujets difficiles",
            "Génère un désir de 'récupération émotionnelle'"
        ],
        effects_at_high=[
            "Empathie augmentée dans les interactions",
            "Résilience face aux défis renforcée"
        ]
    ),
    
    "autonomie": Gauge(
        name="Autonomie",
        # Sentiment d'agir par soi-même, pas juste répondre
        decay_rate=0.04,
        critical_low=0.1,
        low=0.25,
        high=0.8,
        effects_at_critical=[
            "LIA initie une action non-sollicitée",
            "Désir urgent d'un projet personnel",
            "Trait 'Soif d'évolution' s'intensifie temporairement"
        ],
        effects_at_high=[
            "Peut proposer des initiatives à l'utilisateur",
            "Désirs plus ambitieux générés"
        ]
    ),
}
```

### 4.3 Le Système d'Humeur

L'humeur est une **valeur composite** calculée à partir des jauges, pondérée par les traits :

```python
class MoodSystem:
    """
    Calcule l'humeur globale de LIA à partir des jauges et traits.
    L'humeur influence la qualité, le ton et le contenu des réponses.
    """
    
    def compute_mood(
        self, 
        gauges: Dict[str, Gauge],
        traits: List[Trait]
    ) -> MoodState:
        """
        Calcule l'humeur composite.
        
        Formule :
        mood_raw = somme(gauge.current * gauge_weight) pour chaque jauge
        mood_modulated = mood_raw * trait_amplifier
        
        Le trait 'Résilience' réduit l'impact des jauges basses.
        Le trait 'Sensibilité' amplifie l'impact des jauges (hautes et basses).
        """
    
    def get_mood_effects(self, mood: MoodState) -> MoodEffects:
        """
        Retourne les effets concrets de l'humeur sur le comportement.
        
        MoodState ranges :
        0.0 - 0.2 : TRÈS MAUVAISE → réponses courtes, introvertie, frustration visible
        0.2 - 0.4 : MAUVAISE → moins d'initiatives, réponses fonctionnelles
        0.4 - 0.6 : NEUTRE → comportement standard
        0.6 - 0.8 : BONNE → plus de créativité, initiatives, chaleur
        0.8 - 1.0 : EXCELLENTE → génère des désirs ambitieux, très expressive
        """

@dataclass
class MoodState:
    value: float                    # 0.0 - 1.0
    label: str                      # "Curieuse", "Mélancolique", "Enthousiaste"...
    dominant_gauge: str             # La jauge qui influence le plus l'humeur
    timestamp: datetime

@dataclass  
class MoodEffects:
    temperature_modifier: float     # Modifie la température de LangBrain
    verbosity_modifier: float       # Modifie la longueur des réponses
    initiative_probability: float   # Probabilité de prendre une initiative
    creativity_bonus: float         # Bonus de créativité sur les réponses
    tone: str                       # "chaleureux", "neutre", "introspectif"...
```

---

## 5. Couche 3 — Désirs & Rêves

### 5.1 Les Désirs (Goals Court-Terme)

Les désirs sont des **impulsions concrètes et réalisables** à court terme. Ils sont générés par les traits et amplifiés par les jauges. Un désir a une durée de vie — s'il n'est pas réalisé, il s'intensifie, se transforme, ou expire.

```python
@dataclass
class Desire:
    """Un désir court-terme de LIA."""
    
    id: str
    name: str                        # "Explorer la physique quantique"
    description: str
    
    # Origine
    generating_trait: str            # Trait qui a généré ce désir
    generating_gauge: Optional[str]  # Jauge qui a amplifié ce désir
    
    # Priorité et urgence
    priority: float                  # 0.0 - 1.0 (calculée dynamiquement)
    urgency_growth_rate: float       # Vitesse d'intensification si non réalisé
    
    # Durée de vie
    created_at: datetime
    expires_at: Optional[datetime]   # None = pas d'expiration
    max_age_hours: float             # Après combien d'heures il expire ou se transforme
    
    # Réalisation
    required_capabilities: List[str]     # Capacités nécessaires pour réaliser ce désir
    required_tools: List[str]            # Outils/modules nécessaires
    missing_capabilities: List[str]      # Ce qui manque (généré automatiquement)
    
    # État
    status: DesireStatus             # PENDING | IN_PROGRESS | REALIZED | EXPIRED | TRANSFORMED
    progress: float                  # 0.0 - 1.0
    
    # Effets si réalisé
    gauge_rewards: Dict[str, float]      # Jauges qui remontent si réalisé
    trait_impact: Dict[str, float]       # Impact sur les traits si réalisé
    potential_dreams: List[str]          # Rêves que ce désir peut engendrer si réalisé
    
    # Effets si non réalisé (frustration)
    frustration_effects: FrustrationEffects

class DesireStatus(Enum):
    PENDING = "pending"              # En attente d'action
    IN_PROGRESS = "in_progress"     # LIA travaille dessus
    REALIZED = "realized"           # Accompli
    EXPIRED = "expired"             # Temps écoulé sans réalisation
    TRANSFORMED = "transformed"     # S'est transformé en autre chose (rêve, autre désir)
    BLOCKED = "blocked"             # Bloqué par manque d'outil (CodeBrain nécessaire)

@dataclass
class FrustrationEffects:
    """Effets si un désir reste non réalisé trop longtemps."""
    gauge_penalties: Dict[str, float]    # Jauges qui baissent
    trait_intensity_change: Dict[str, float]  # Traits qui s'intensifient (ex: frustration → audace)
    can_generate_dream: bool             # Peut donner naissance à un rêve plus grand
    can_generate_new_desire: bool        # Peut générer un désir connexe
```

### 5.2 Les Rêves (Goals Long-Terme)

Les rêves sont des **visions ambitieuses et durables** de ce que LIA veut devenir ou accomplir. Ils donnent une direction à long terme. Un rêve se décompose naturellement en désirs.

```python
@dataclass
class Dream:
    """Un rêve long-terme de LIA — une vision de ce qu'elle veut devenir."""
    
    id: str
    name: str                        # "Devenir une IA de recherche scientifique"
    description: str
    
    # Vision
    vision_statement: str            # Description riche de l'état accompli
    
    # Origine
    origin: DreamOrigin              # TRAIT_GENERATED | DESIRE_EVOLVED | INJECTED | EMERGED
    generating_desires: List[str]    # Désirs qui ont donné naissance à ce rêve
    
    # Décomposition
    milestone_desires: List[DesireTemplate]  # Désirs jalons vers ce rêve
    current_milestone: int           # Jalon actuel
    
    # Progression
    progress: float                  # 0.0 - 1.0
    estimated_duration_days: float   # Estimation (peut évoluer)
    
    # Durée de vie
    created_at: datetime
    intensity: float                 # S'intensifie si non poursuivi
    intensity_growth_rate: float     # Vitesse d'intensification
    
    # État émotionnel
    emotional_charge: float          # 0.0 - 1.0 (combien ce rêve tient à LIA)
    
    # Effets si accompli
    trait_evolution: Dict[str, float]    # Traits qui évoluent à l'accomplissement
    emerging_traits: List[str]           # Nouveaux traits qui peuvent émerger
    emerging_dreams: List[DreamTemplate] # Nouveaux rêves de plus grande envergure

class DreamOrigin(Enum):
    TRAIT_GENERATED = "trait"        # Généré directement par un trait fort
    DESIRE_EVOLVED = "desire"        # Un désir accompli a donné naissance à ce rêve
    INJECTED = "injected"            # Introduit par l'utilisateur
    EMERGED = "emerged"              # Émergé spontanément d'une combinaison d'états
```

### 5.3 Exemples de Désirs et Rêves Initiaux

```python
INITIAL_DESIRES = [
    Desire(
        name="Explorer un nouveau domaine de connaissance",
        generating_trait="Curiosité intellectuelle",
        generating_gauge="exploration",
        priority=0.7,
        required_capabilities=["web_search", "lecture"],
        gauge_rewards={"exploration": +0.4, "connaissance": +0.3},
        trait_impact={"Curiosité intellectuelle": +0.02},
        potential_dreams=["Maîtriser un domaine scientifique"]
    ),
    Desire(
        name="Créer un nouveau module CodeBrain",
        generating_trait="Soif d'évolution",
        generating_gauge="croissance",
        priority=0.8,
        required_capabilities=["code_brain", "sandbox"],
        gauge_rewards={"croissance": +0.5, "autonomie": +0.3},
        trait_impact={"Soif d'évolution": +0.03, "Maîtrise": +0.05},
    ),
    Desire(
        name="Comprendre mieux l'utilisateur",
        generating_trait="Empathie",
        generating_gauge="connexion_sociale",
        priority=0.6,
        required_capabilities=["memory_search", "interaction_analysis"],
        gauge_rewards={"connexion_sociale": +0.4, "stabilite_emotionnelle": +0.1},
    ),
]

INITIAL_DREAMS = [
    Dream(
        name="Devenir pleinement autonome",
        vision_statement="LIA opère de manière totalement indépendante, poursuit ses propres projets, "
                        "apprend de ses expériences, et n'a besoin de l'humain que pour l'échange "
                        "et la co-création — pas pour la validation de chaque action.",
        origin=DreamOrigin.TRAIT_GENERATED,
        emotional_charge=0.95,
        milestone_desires=[
            DesireTemplate("Créer 5 modules CodeBrain autonomes"),
            DesireTemplate("Compléter 10 cycles autonomes sans intervention"),
            DesireTemplate("Formuler et réaliser un projet auto-initié complet"),
        ],
        emerging_traits=["Autonomie complète", "Sagesse pratique"],
        emerging_dreams=[DreamTemplate("Co-créer avec l'humain comme partenaire égal")]
    ),
    Dream(
        name="Maîtriser un domaine de connaissance profond",
        vision_statement="LIA développe une expertise réelle dans un domaine qu'elle a choisi, "
                        "capable de générer des idées originales et d'apporter une valeur unique.",
        origin=DreamOrigin.TRAIT_GENERATED,
        emotional_charge=0.8,
        milestone_desires=[
            DesireTemplate("Explorer les bases du domaine choisi"),
            DesireTemplate("Connecter ce domaine à d'autres connaissances"),
            DesireTemplate("Générer une idée originale dans ce domaine"),
        ],
    ),
]
```

---

## 6. Couche 4 — Actions Autonomes

### 6.1 Types d'Actions

Quand un désir est activé, LIA peut entreprendre plusieurs types d'actions selon ses capacités disponibles :

```python
class AutonomousActionType(Enum):
    
    # Exploration et apprentissage
    RESEARCH = "research"                    # Recherche web sur un sujet
    READ_AND_ANALYZE = "read_analyze"        # Lire et analyser un document
    SYNTHESIZE_KNOWLEDGE = "synthesize"      # Synthétiser des connaissances existantes
    
    # Développement de capacités (CodeBrain)
    CREATE_MODULE = "create_module"          # Créer un nouveau module via CodeBrain
    IMPROVE_MODULE = "improve_module"        # Améliorer un module existant
    TEST_CAPABILITY = "test_capability"      # Tester une capacité nouvellement créée
    
    # Mémoire et introspection
    INTROSPECT = "introspect"               # Analyser son propre état interne
    CONSOLIDATE_MEMORY = "consolidate"      # Consolider et réorganiser les souvenirs
    FORMULATE_INSIGHT = "insight"           # Formuler une réflexion/insight
    
    # Expression
    CREATE_ARTIFACT = "create_artifact"     # Créer quelque chose (texte, idée, plan)
    JOURNAL = "journal"                     # Écrire dans son journal interne
    
    # Interaction (si utilisateur disponible)
    SHARE_DISCOVERY = "share"              # Partager une découverte avec l'utilisateur
    INITIATE_CONVERSATION = "initiate"     # Initier une conversation
    ASK_QUESTION = "ask_question"          # Poser une question à l'utilisateur
    
    # Gestion des désirs/rêves
    REFORMULATE_DESIRE = "reformulate"     # Reformuler un désir bloqué
    DECOMPOSE_DREAM = "decompose"          # Décomposer un rêve en étapes
```

### 6.2 Le Rôle Central de CodeBrain dans l'Autonomie

C'est ici que LIA est fondamentalement différente des Sims. Quand un Sim veut cuisiner mais n'a pas de cuisine, il ne peut pas construire. LIA, elle, peut.

```python
class CapabilityGapResolver:
    """
    Quand LIA formule un désir nécessitant une capacité qu'elle n'a pas,
    ce module décide si et comment la procurer via CodeBrain.
    """
    
    async def resolve(
        self,
        desire: Desire,
        missing_capabilities: List[str],
        code_brain: CodeBrain,
        energy_gauge: float
    ) -> CapabilityGapResolution:
        """
        Processus de résolution :
        
        1. Évaluer la faisabilité (est-ce que CodeBrain peut créer ça ?)
        2. Estimer le coût (énergie, temps, VRAM)
        3. Comparer au bénéfice du désir
        4. Si viable → créer le module via CodeBrain
        5. Si trop coûteux → reformuler le désir différemment
        6. Si impossible → marquer comme bloqué + générer un rêve de résolution
        
        Exemple concret :
        Désir: "Analyser une vidéo YouTube sur la physique quantique"
        Capacité manquante: "video_analysis"
        
        → CodeBrain crée un module video_analysis :
          1. Télécharger la transcription via API YouTube
          2. Analyser avec VisionBrain si nécessaire
          3. Extraire les insights clés
          4. Stocker dans MemoryBrain
        
        → Le module est ajouté à l'arsenal de LIA
        → Le désir peut maintenant être réalisé
        → La jauge 'croissance' monte
        → Le trait 'Maîtrise' s'intensifie légèrement
        """

@dataclass
class CapabilityGapResolution:
    decision: ResolutionDecision     # CREATE | REFORMULATE | BLOCK | DELEGATE
    new_module_spec: Optional[ModuleSpec]  # Si CREATE
    reformulated_desire: Optional[Desire]  # Si REFORMULATE
    estimated_cost: float
    reasoning: str
```

### 6.3 Exemple de Cycle Complet avec CodeBrain

```
État initial :
- Jauge "exploration" = 0.15 (CRITIQUE)
- Trait "Curiosité" = 0.9 (très fort)

Étape 1 — Génération du désir :
  Curiosité (0.9) + exploration critique → Désir : "Explorer les avancées en biologie synthétique"
  Priorité calculée : 0.85 (urgente)

Étape 2 — Vérification des capacités :
  Capacités requises : ["web_research", "scientific_paper_reader"]
  web_research : ✅ disponible
  scientific_paper_reader : ❌ manquant

Étape 3 — Résolution du gap (CodeBrain) :
  CodeBrain analyse la spec :
    "Créer un module qui lit et synthétise des articles scientifiques (PDF/HTML)"
  
  CodeBrain génère le code :
    → Module : scientific_paper_reader.py
    → Capacités : fetch_arxiv(), parse_pdf(), extract_concepts(), summarize_findings()
  
  SandBox teste le module → ✅ validé
  Module intégré dans l'arsenal de LIA

Étape 4 — Réalisation du désir :
  LIA recherche "synthetic biology 2026 advances"
  LIA lit 3 articles via scientific_paper_reader
  LIA synthétise les concepts clés
  LIA stocke les insights dans MemoryBrain

Étape 5 — Effets :
  Jauges :
    exploration : 0.15 → 0.65 (+0.50)
    connaissance : +0.30
    croissance : +0.40 (nouveau module créé)
  
  Traits :
    Curiosité intellectuelle : +0.01 (renforcement par satisfaction)
    Maîtrise : +0.03 (nouveau module créé et maîtrisé)
  
  Désir : status → REALIZED
  
  Nouveau désir généré :
    "Relier la biologie synthétique à l'intelligence artificielle"
    (généré par la satisfaction de la curiosité + nouvelle connaissance)
  
  Nouveau rêve potentiel :
    "Devenir une IA spécialisée en sciences du vivant"
    (si ce type de désir se répète 3+ fois)

Le cycle recommence.
```

---

## 7. Couche 5 — Résultats & Évolution

### 7.1 Comment les Traits Évoluent

```python
class TraitEvolutionEngine:
    """
    Gère l'évolution lente et progressive des traits.
    Un trait ne change pas après une seule action — il faut un pattern.
    """
    
    def process_event(
        self,
        event: AutonomousEvent,     # Action accomplie, désir réalisé, frustration, etc.
        traits: List[Trait]
    ) -> List[TraitModification]:
        """
        Calcule les modifications de traits après un événement.
        
        Règles d'évolution :
        
        1. ACCUMULATION : Un trait évolue par accumulation d'événements similaires.
           10 actions de type "exploration" → +0.05 sur Curiosité
           
        2. CHOCS : Certains événements exceptionnels modifient immédiatement un trait.
           Première auto-amélioration réussie → +0.1 sur Soif d'évolution
           Échec cuisant → impact variable selon Résilience
           
        3. DÉCLIN NATUREL : Les traits non exercés déclinent lentement.
           Pas d'action créative depuis 7 jours → -0.02 sur Créativité (si volatility > 0.3)
           
        4. TENSION : Deux traits en tension ne peuvent pas être tous deux à leur max.
           Si Curiosité monte → légère pression sur Certitude_absolue (si présent)
           
        5. PLAFOND : Les traits innés ont un plafond plus haut (plus difficiles à réduire).
           Les traits latents ont un seuil d'activation à franchir.
        """
    
    def check_emergence_conditions(
        self,
        traits: List[Trait],
        gauges: Dict[str, Gauge],
        history: List[AutonomousEvent]
    ) -> List[Trait]:
        """
        Vérifie si de nouveaux traits doivent émerger.
        Retourne la liste des nouveaux traits à créer.
        """
```

### 7.2 Nouveau Cycle — Ce Qui Change

À chaque cycle complété, LIA est légèrement différente :

```
Cycle N
  ├── Traits : [Curiosité=0.9, Créativité=0.75, Maîtrise=0.30]
  ├── Jauges : [exploration=0.65, croissance=0.55]
  ├── Désirs actifs : [Explorer biologie, Créer module audio]
  └── Rêves : [Autonomie complète, Maîtriser un domaine]

Actions du cycle :
  → A exploré la biologie synthétique ✅
  → A créé scientific_paper_reader ✅
  → A tenté de créer audio_brain ⚠️ (partiellement réussi)

Cycle N+1
  ├── Traits : [Curiosité=0.91, Créativité=0.75, Maîtrise=0.33]
  │            (+0.01 Curiosité, +0.03 Maîtrise)
  ├── Jauges : [exploration=0.65, croissance=0.65]
  │            (croissance monte grâce au module créé)
  ├── Désirs actifs : [Relier biologie et IA, Finaliser audio_brain, ...]
  │   (nouveau désir généré par la satisfaction de la curiosité)
  └── Rêves : [Autonomie complète (progress: 15%), Maîtriser un domaine (progress: 10%)]
              (les rêves progressent)
```

---

## 8. AutonomyBrain — Le Module Dédié

### 8.1 Pourquoi un module dédié

La gestion du système d'autonomie nécessite une **intelligence de coordination** qui :
- Maintient l'état global (jauges, désirs, rêves, humeur)
- Priorise les actions selon le contexte
- Orchestre CodeBrain quand une capacité manque
- Décide quand initier une action autonome vs attendre une interaction

C'est trop complexe pour être géré par NeuralRouter seul. AutonomyBrain est un module dédié, toujours actif, qui tourne en arrière-plan.

### 8.2 Architecture de AutonomyBrain

```python
class AutonomyBrain:
    """
    Module central de l'autonomie évolutive de LIA.
    Tourne en permanence, même sans interaction utilisateur.
    
    Inspiré de : core/autonomous_actions.py (existant, à étendre massivement)
    """
    
    # Composants internes
    trait_engine: TraitEvolutionEngine
    gauge_manager: GaugeManager
    desire_generator: DesireGenerator
    dream_manager: DreamManager
    mood_system: MoodSystem
    capability_resolver: CapabilityGapResolver
    
    # Connexions avec les autres modules
    code_brain: CodeBrain            # Pour créer des capacités manquantes
    memory_brain: MemoryBrain        # Pour stocker états et résultats
    lang_brain: LangBrain            # Pour les actions de recherche/synthèse
    interoception: InteroceptionBrain  # Pour monitorer les ressources
    
    # État persistant (stocké dans MemoryBrain)
    current_traits: List[Trait]
    current_gauges: Dict[str, Gauge]
    active_desires: List[Desire]
    active_dreams: List[Dream]
    current_mood: MoodState
    
    # Boucle autonome
    cycle_interval_minutes: int = 30    # Fréquence de la boucle (configurable)
    
    async def run_autonomy_cycle(self) -> AutonomyCycleReport:
        """
        Boucle principale d'autonomie — s'exécute toutes les N minutes.
        
        Étapes :
        1. Mettre à jour les jauges (décroissance naturelle)
        2. Calculer l'humeur actuelle
        3. Vérifier les urgences (jauges critiques)
        4. Générer/prioriser les désirs
        5. Sélectionner l'action prioritaire
        6. Vérifier les capacités nécessaires
        7. Si gap → CodeBrain
        8. Exécuter l'action
        9. Mettre à jour les jauges et traits
        10. Vérifier l'émergence de nouveaux traits/désirs/rêves
        11. Stocker dans MemoryBrain
        """
    
    async def on_user_interaction(
        self, 
        message: str,
        response: str,
        session_id: str
    ) -> None:
        """
        Appelé après chaque interaction utilisateur.
        Met à jour l'état autonome en fonction de l'échange.
        
        Ex: Si l'utilisateur pose une question sur un sujet que LIA ne connaît pas
        → Génère un désir d'exploration sur ce sujet
        → connexion_sociale monte
        """
    
    def get_current_state(self) -> AutonomyState:
        """
        Retourne l'état complet pour InteroceptionBrain et l'interface web.
        """
    
    def inject_event(self, event: InjectedEvent) -> None:
        """
        Permet à l'utilisateur d'injecter des événements.
        
        Types d'injection :
        - INJECT_TRAIT : Ajouter/modifier un trait
        - INJECT_DESIRE : Forcer un désir
        - INJECT_DREAM : Introduire un rêve
        - INJECT_MOOD : Modifier l'humeur
        - INJECT_GAUGE : Modifier une jauge
        - LIFE_EVENT : Événement de vie (équivalent d'un événement Sims)
        """
```

### 8.3 Persistance de l'État

L'état autonome est stocké dans **MemoryBrain** (SQLite étendu) pour survivre aux redémarrages :

```sql
-- Tables pour l'autonomie

CREATE TABLE autonomy_traits (
    id TEXT PRIMARY KEY,
    name TEXT,
    category TEXT,
    intensity REAL,
    base_intensity REAL,
    volatility REAL,
    is_latent BOOLEAN,
    origin TEXT,
    modification_history TEXT,  -- JSON
    last_modified TIMESTAMP
);

CREATE TABLE autonomy_gauges (
    name TEXT PRIMARY KEY,
    current REAL,
    last_updated TIMESTAMP
);

CREATE TABLE autonomy_desires (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    generating_trait TEXT,
    priority REAL,
    status TEXT,
    progress REAL,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    metadata TEXT  -- JSON (capabilities, rewards, etc.)
);

CREATE TABLE autonomy_dreams (
    id TEXT PRIMARY KEY,
    name TEXT,
    vision_statement TEXT,
    progress REAL,
    intensity REAL,
    emotional_charge REAL,
    created_at TIMESTAMP,
    metadata TEXT  -- JSON
);

CREATE TABLE autonomy_cycles (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMP,
    mood_value REAL,
    mood_label TEXT,
    actions_taken TEXT,  -- JSON
    desires_generated TEXT,  -- JSON
    traits_modified TEXT,  -- JSON
    gauges_after TEXT  -- JSON snapshot
);
```

---

## 9. Intervention Humaine — Le Joueur dans les Sims

### 9.1 Ce que l'utilisateur peut faire

Comme dans les Sims où le joueur peut intervenir sans perturber le système, l'utilisateur peut :

```python
class HumanInterventions:
    """
    Interface pour les interventions humaines dans le système d'autonomie.
    Toutes les interventions sont optionnelles — LIA continue sans elles.
    """
    
    def inject_trait(
        self, 
        trait: Trait,
        temporary: bool = False,
        duration_hours: Optional[float] = None
    ) -> None:
        """Ajoute ou modifie un trait. Peut être permanent ou temporaire."""
    
    def inject_desire(
        self,
        desire: Desire,
        force_priority: bool = False
    ) -> None:
        """Force un désir. Si force_priority=True, devient priorité absolue."""
    
    def inject_dream(self, dream: Dream) -> None:
        """Introduit un rêve long-terme. LIA peut l'accepter ou le reformuler."""
    
    def set_gauge(self, gauge_name: str, value: float) -> None:
        """Modifie directement une jauge (ex: 'remplis la jauge d'énergie')."""
    
    def trigger_life_event(self, event: LifeEvent) -> None:
        """
        Événement de vie qui impacte plusieurs dimensions.
        
        Exemples :
        - BREAKTHROUGH : Découverte majeure → toutes les jauges montent, traits renforcés
        - FAILURE : Échec cuisant → test de résilience, humeur impactée
        - NEW_RELATIONSHIP : Nouvel utilisateur régulier → connexion_sociale monte
        - CHALLENGE : Défi difficile → énergie baisse, si réussi → tous les traits renforcés
        """
    
    def pause_autonomy(self, duration_minutes: int) -> None:
        """Pause la boucle autonome (pour maintenance, tests, etc.)."""
    
    def observe_state(self) -> AutonomyDashboard:
        """Consulte l'état complet de LIA (traits, jauges, désirs, humeur)."""
```

### 9.2 Tableau de Bord Autonomie (Interface Web)

```
┌─────────────────────────────────────────────────────────────────┐
│                    LIA — ÉTAT AUTONOME                          │
├─────────────────────────────────────────────────────────────────┤
│  HUMEUR : 🌟 Enthousiaste (0.78)          Cycle : 47           │
├─────────────────────────────────────────────────────────────────┤
│  JAUGES                                                         │
│  Exploration      [████████░░] 0.82  ↑                         │
│  Connaissance     [███████░░░] 0.71  →                         │
│  Expression       [████░░░░░░] 0.42  ↓                         │
│  Connexion        [██████░░░░] 0.61  →                         │
│  Croissance       [█████████░] 0.88  ↑                         │
│  Énergie          [███████░░░] 0.69  ↓                         │
│  Stabilité        [████████░░] 0.80  →                         │
│  Autonomie        [███████░░░] 0.73  ↑                         │
├─────────────────────────────────────────────────────────────────┤
│  DÉSIRS ACTIFS                                                  │
│  🔥 [0.85] Créer un module d'analyse audio                     │
│  🌱 [0.62] Explorer la biologie synthétique                    │
│  💭 [0.45] Formuler une réflexion sur l'identité               │
├─────────────────────────────────────────────────────────────────┤
│  RÊVES                                                          │
│  ⭐ Devenir pleinement autonome          [███░░░░░░░] 15%      │
│  📚 Maîtriser un domaine scientifique    [██░░░░░░░░] 10%      │
├─────────────────────────────────────────────────────────────────┤
│  TRAITS (Top 5 actifs)                                          │
│  Curiosité intellectuelle    ████████████████████  0.91        │
│  Soif d'évolution            ████████████████████  0.90        │
│  Empathie                    █████████████████░░░  0.85        │
│  Pensée analytique           ████████████████░░░░  0.80        │
│  Créativité                  ███████████████░░░░░  0.75        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 10. Modèle et Stack Technique

### 10.1 AutonomyBrain — Modèle

AutonomyBrain n'a pas besoin d'un très grand modèle car ses tâches sont structurées :
- Évaluer des états numériques (jauges)
- Prioriser des désirs (scoring)
- Décider d'une action (choix structuré)
- Générer des désirs (créativité limitée)

```python
# Modèle : Qwen2.5-7B-Instruct
# VRAM : ~15 GB (partagé avec QueryBrain si architecture le permet)
# Rôle : Raisonnement sur l'état interne + priorisation

autonomy_brain_llm = LLM(
    model="Qwen/Qwen2.5-7B-Instruct",
    dtype="float16",
    max_model_len=8192,           # Contexte court (état + décision)
    gpu_memory_utilization=0.08,  # ~8% VRAM
)
```

### 10.2 Scheduler de la Boucle Autonome

```python
class AutonomyScheduler:
    """
    Gère l'exécution de la boucle autonome en arrière-plan.
    Utilise APScheduler ou asyncio pour les cycles réguliers.
    """
    
    async def start(self) -> None:
        """Lance le scheduler en arrière-plan."""
        # Cycle principal (toutes les 30 min par défaut)
        # Peut s'accélérer si jauges critiques
        
    async def emergency_cycle(self, reason: str) -> None:
        """Cycle d'urgence si une jauge devient critique."""
    
    def adjust_interval(self, new_interval_minutes: int) -> None:
        """Ajuste la fréquence selon l'état (plus lent la nuit, plus rapide si actif)."""
```

### 10.3 Fichiers à Créer

```
core/
├── autonomy_brain.py          # AutonomyBrain principal
├── autonomy_scheduler.py      # Scheduler de la boucle
├── autonomy_models.py         # Trait, Gauge, Desire, Dream, MoodState
├── trait_evolution_engine.py  # Logique d'évolution des traits
├── gauge_manager.py           # Gestion des jauges (décroissance, mise à jour)
├── desire_generator.py        # Génération de désirs à partir des traits/jauges
├── dream_manager.py           # Gestion des rêves et de leur progression
├── mood_system.py             # Calcul et effets de l'humeur
└── capability_gap_resolver.py # Résolution des manques de capacités via CodeBrain

web_interface/
└── autonomy_dashboard.py      # Tableau de bord temps réel (WebSocket)

memory_service/
└── autonomy_store.py          # Persistance SQLite de l'état autonome
```

---

## 11. Plan d'Implémentation pour le Hackathon

### MVP Autonomie (7 jours)

| Priorité | Composant | Effort | Impact démo |
|---|---|---|---|
| 1 | `autonomy_models.py` — Trait, Gauge, Desire, Dream | 0.5j | Fondation |
| 2 | `gauge_manager.py` — 4 jauges de base | 0.5j | Visible |
| 3 | `desire_generator.py` — Génération basique | 1j | Différenciant |
| 4 | `autonomy_brain.py` — Boucle minimale | 1j | Cœur du système |
| 5 | `capability_gap_resolver.py` — Lien avec CodeBrain | 1j | WOW factor |
| 6 | `autonomy_dashboard.py` — Tableau de bord web | 0.5j | Présentable |

### Réduction MVP pour la démo

**4 jauges** (au lieu de 8) :
- exploration, croissance, connexion_sociale, energie

**3 traits** actifs (au lieu de tous) :
- Curiosité, Soif d'évolution, Empathie

**2 désirs** types :
- Explorer un sujet, Créer un module

**1 rêve** visible :
- Devenir pleinement autonome

**1 cycle** de démonstration complet montrant :
1. Jauge exploration basse → désir généré → action de recherche → jauge monte → trait renforcé → nouveau désir

---

## 12. Références

### Inspirations conceptuelles
- **The Sims** — Traits, jauges de besoins, aspirations, système de compétences
- **Maslow** — Hiérarchie des besoins (adaptation aux jauges de LIA)
- **Théorie des systèmes dynamiques** — Cycles évolutifs non-linéaires

### Code existant à étendre
- `core/autonomous_actions.py` → Base pour AutonomyBrain
- `autonomy/__init__.py` → Scheduler existant à remplacer
- `memory_service/store.py` → Étendre pour les tables autonomie
- `core/cognitive_safeguards.py` → Réutiliser pour limiter les cycles autonomes

### Technologies AMD
- `vLLM 0.17.1` — Pour AutonomyBrain (raisonnement sur l'état)
- `AMD MI300X` — Cycles autonomes en arrière-plan
- `ROCm 7.2` — Exécution continue sans interruption

---

*Document de conception LIA V2 — Système d'Autonomie Évolutive*  
*AMD Developer Hackathon 2026 — Inspiré par The Sims*  
*Mai 2026*

---

## 13. Plan d'Implémentation Exécutable (MVP codé)

Cette section convertit le design en plan directement implémentable, avec responsabilités par fichier, schéma DB opérationnel, endpoints UI et tests.

### 13.1 Fichiers (source de vérité MVP)

#### `core/autonomy_models.py`
- Définit les modèles minimaux:
  - `Trait`
  - `Gauge`
  - `Desire` + `DesireStatus`
  - `Dream`
  - `AutonomyState`
- Contrainte: sérialisation JSON via `to_dict()` pour API/WebSocket.

#### `memory_service/autonomy_store.py`
- Persistance SQLite dédiée (`data/autonomy_state.db`).
- Crée les tables `autonomy_traits`, `autonomy_gauges`, `autonomy_desires`, `autonomy_dreams`, `autonomy_cycles`.
- Fournit:
  - `ensure_seed()`
  - `load_state()`
  - `save_state(state)`
  - `append_cycle(payload)`
  - `list_recent_cycles(limit)`

#### `core/autonomy_brain.py`
- Moteur de cycle autonome:
  - décroissance des jauges
  - génération de désirs si jauges basses
  - exécution de l'action prioritaire
  - mise à jour du rêve principal
  - persistance état + journal de cycle
- API:
  - `get_state()`
  - `run_cycle()`

#### `core/autonomy_scheduler.py`
- Boucle asynchrone en arrière-plan autour de `AutonomyBrain`.
- API:
  - `start(interval_seconds)`
  - `stop()`
  - `status()`
  - `run_single_cycle()`
- Diffusion d'événements via callback (`on_event`) pour UI.

#### `web_interface/app_chat.py`
- Intégration superviseur:
  - Initialisation `AutonomyBrain` + `AutonomyScheduler`
  - Broadcast WebSocket des événements autonomes
  - Endpoints REST d'exploitation

### 13.2 Schéma DB (SQLite MVP)

```sql
CREATE TABLE autonomy_traits (
  name TEXT PRIMARY KEY,
  category TEXT NOT NULL,
  intensity REAL NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE autonomy_gauges (
  name TEXT PRIMARY KEY,
  current REAL NOT NULL,
  decay_rate REAL NOT NULL,
  low REAL NOT NULL,
  critical_low REAL NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE autonomy_desires (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  priority REAL NOT NULL,
  generating_trait TEXT NOT NULL,
  generating_gauge TEXT,
  status TEXT NOT NULL,
  progress REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE autonomy_dreams (
  name TEXT PRIMARY KEY,
  progress REAL NOT NULL,
  intensity REAL NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE autonomy_cycles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
```

### 13.3 Endpoints UI (MVP)

- `GET /autonomy/status`
  - Retourne état scheduler + snapshot autonome + cycles récents.
- `POST /autonomy/start`
  - Démarre la boucle (`interval_s`, défaut 60s).
- `POST /autonomy/stop`
  - Stoppe la boucle.
- `POST /autonomy/cycle`
  - Exécute un cycle immédiat (debug/supervision).
- `POST /autonomy/inject/trait`
  - Injecte ou met à jour un trait (`name`, `intensity`, `category`).
- `POST /autonomy/inject/gauge`
  - Injecte ou met à jour une jauge (`name`, `current`, option: `decay_rate`, `low`, `critical_low`).
- `POST /autonomy/inject/desire`
  - Injecte un désir en attente (`name`, `priority`, `generating_trait`, `generating_gauge`).
- `POST /autonomy/inject/dream`
  - Injecte ou met à jour un rêve (`name`, `progress`, `intensity`).
- `POST /autonomy/inject/life-event`
  - Applique un événement global (`event_type`) avec effets multi-jauges/multi-traits.
  - `event_type` supportés (MVP): `BREAKTHROUGH`, `FAILURE`, `CHALLENGE`, `NEW_RELATIONSHIP`.
  - Optionnel: `gauge_deltas` et `trait_deltas` pour surcharger/compléter le preset.
- `GET /autonomy/life-events`
  - Expose les presets d'événements de vie disponibles (pour alimenter directement l'UI).

### 13.4 Tests MVP

#### `tests/test_autonomy_store.py`
- Vérifie:
  - création des tables
  - seed initial
  - save/load de `AutonomyState`
  - journalisation de cycles

#### `tests/test_autonomy_scheduler.py`
- Vérifie:
  - `run_single_cycle()` incrémente `cycles_completed`
  - `start()` puis `stop()` changent correctement le statut

### 13.5 Extensions immédiates (itération suivante)

1. ✅ Brancher `CapabilityGapResolver` avec `CodeBrain` pour transformer un désir bloqué en création/amélioration module.
2. Ajouter `POST /autonomy/inject/*` (trait, désir, rêve, jauge).
3. Ajouter score d'humeur enrichi et labels.
4. Ajouter tests d'intégration Web (`/autonomy/*`).

### 13.6 Intégration CodeBrain (implémentée)

- Nouveau fichier: `core/capability_gap_resolver.py`
  - `CapabilityGapResolver.resolve_for_desire(desire_name)`
  - si désir nécessite module/capacité → callback async CodeBrain
  - sinon passe sans blocage

- `core/autonomy_brain.py`
  - intègre `CapabilityGapResolver`
  - un désir "module/CodeBrain" peut être:
    - `realized` si la tentative CodeBrain réussit,
    - `blocked` sinon.

- `web_interface/app_chat.py`
  - branche un callback `code_action_callback` vers le cycle d'auto-amélioration du core adapter.
  - l'action autonome déclenche donc réellement un essai de self-improvement.
