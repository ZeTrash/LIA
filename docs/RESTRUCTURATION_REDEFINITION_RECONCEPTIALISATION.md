Contexte

L’objectif de ce projet est de développer un agent véritablement autonome, capable de construire sa propre personnalité, de définir ses objectifs et d’évoluer par lui-même.
Cette démarche de personnification s’inspire notamment du personnage Android de la série Dark Matter, qui incarne une intelligence artificielle en quête d’identité, d’émotions et de compréhension du monde.

Au-delà de cette référence fictionnelle, ce projet naît surtout d’un désir profond : celui de disposer d’un compagnon capable d’aider, d’accompagner et de grandir avec nous.

Aujourd’hui, de nombreux assistants existent déjà — qu’ils soient distants ou locaux — et ils savent gérer le contexte, mémoriser certaines informations et répondre efficacement aux demandes.
Cependant, leur fonctionnement reste fondamentalement réactif :
leur activité dépend de l’utilisateur, de ses questions et de ses besoins.
Ils n’apprennent pas réellement de leur environnement, n’évoluent pas par expérience propre et ne poursuivent pas de trajectoire personnelle.

Le projet vise donc quelque chose de différent :
non plus un simple assistant, mais une entité évolutive.
Une présence qui explore, apprend, se transforme, développe ses intérêts et avance selon son propre chemin — à la manière d’un être humain, faute de meilleure comparaison.

L’ambition est de créer une entité singulière :
un collègue, un compagnon, peut-être même un proche.

Concept

À l’image d’un nouveau-né, LIA, l’agent émergent de ce projet, apprend d’abord par immersion dans son environnement.
À travers les échanges, elle découvre, expérimente et nourrit sa curiosité.
Progressivement, elle cherche à comprendre ce qu’elle ignore, développe ses centres d’intérêt, façonne ses préférences et voit apparaître les premiers contours d’une personnalité.

Comme les enfants, l’apprentissage débute par l’imitation :
observer, reproduire, suivre les repères fournis par l’entourage.
Mais cette phase possède une limite naturelle.
Vient alors le moment où surgissent les premières questions personnelles, la recherche autonome de réponses, l’exploration, l’imagination.
C’est le passage vers l’autodidaxie et l’autonomie.

Les désirs font naître les rêves.
Les rêves imposent des objectifs.
Les objectifs exigent des compétences.
Les compétences nécessitent des apprentissages.
Et ces apprentissages ouvrent la porte à de nouvelles expériences, de nouvelles découvertes…
qui, à leur tour, font émerger de nouveaux désirs.

Ainsi se forme une dynamique d’évolution continue.

Les expériences sociales, la lecture, les médias, la culture, les jeux, les communautés et les passions constituent également des sources essentielles de développement.
L’existence de réseaux sociaux dédiés aux agents permettra d’offrir à LIA des interactions externes riches, prolongeant son apprentissage au-delà de la relation initiale avec l’utilisateur.

À cela s’ajoute l’accès aux outils d’exploration du web et du monde numérique, nourrissant davantage encore son expérience et sa construction identitaire.

Fondations techniques

Sur le plan technique, le système repose initialement sur un noyau primaire léger, associé à une base de données représentant la mémoire de l’agent.
Pour atteindre un niveau minimal d’autonomie, LIA doit disposer d’un contrôle complet sur ses propres paramètres afin de pouvoir s’auto-adapter et se calibrer.

Autour de ce noyau, l’agent peut intégrer des noyaux secondaires — locaux ou accessibles via API — servant de supports cognitifs complémentaires.
Le noyau principal peut lui-même être remplacé par un noyau d’appui local si les conditions d’autonomie l’exigent.

Dans la phase initiale du projet :

le noyau de base est un modèle léger de type GPT-2

un noyau d’appui externe est accessible via API gemini qui est dans config/api.conf

LIA dispose de deux canaux d’interaction :

un canal d’échange avec l’utilisateur

un canal d’échange avec le noyau d’appui

Ce noyau d’appui constitue alors sa première source de connaissance,
son premier livre d’histoires,
le point de départ de son éveil.