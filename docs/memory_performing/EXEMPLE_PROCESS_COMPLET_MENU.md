 Ici est decrit comment fonctionne le processus de la mémoire et de la planification cognitive sous forme d'exemple. C'est comme un bot telegram mais c'est l'agent qui doit répondre au menu proposée par le bot.

 Comme contexte, on a une requettes et ces listes de choix ou d'action que L'agent/LIA peut effectuer et ainsi que les patternes que LIA utilise en préference ou celle la plus efficace. Quels sont ces listes de choix ou d'action? C'est à revoir mais j'imagine que l'on propose des informations important simple:

 --Informations de base--
 1. Consulter patternes préférée.
 2. Consulter ma mémoire et me connaitre. 
 3. Repondre au requette de l'utilisateur. 
 Donc ici l'agent ne peux repondre que par 1. ou 2.

 Puis selon le choix, on offre d'autres champs d'action, par exemple la suite de 2. pourrait être:
 --Information génerale--
 1. Connaitre mon identité. 
 2. Connaitre mes traites. 
 3. Connaitre mon environnement/mes capacitées.
 4. Consulter ma mémoire. 
 5. Repondre au requette de l'utilisateur. 
 6. Revenir au choix des informations de base.

 Puis selon le choix avoir d'autres options. Exemple pour la suite 4. on peut penser à avoir:
 --Information spécifique--
 1. Consulter les n dernière du choix 4 dans la mémoire? 
 3. Consulter un enregistement en particulier du choix 4 dans la mémoire?
 4. Voir tout les enregistements du choix 4 dans la mémoire?
 5. Repondre au requette de l'utilisateur?
 6. Revenir au choix des informations génerale.


 Un pattern c'est  une suite d'action que l'agent à memoriser et qui a été efficace pour répondre à une requette.
 Exemple:
 - Requette: "Qui es-tu ?"
 - Pattern: 2, 3, 1, 3, 5.


 Exemple 1:
     - Requette: "Qui es-tu ?"

     - Prompt Envoyée à l'agent: "Une requette est arrivée. Voici la liste d'action de base possible.
         1. Consulter patternes préférée.
         2. Voir la requette de l'utilisateur.
         3. Consulter ma mémoire et me connaitre. 
         4. Repondre au requette de l'utilisateur. 
         Important: Repondre uniquement par 1 ou 2 ou 3 ou 4" 

     - Réponse de l'agent au prompt envoyée: 2

     - Mémorisation du choix pour l'apprentissage des patternes.

     - Prompt Envoyée à l'agent: 
         "Vous avez choisi l'action de base voir la requette de l'utilisateur. 
         Voici la requette de l'utilisateur: "Qui es-tu ?"
         Voici la liste d'action de base possible.
         1. Consulter patternes préférée.
         2. Voir la requette de l'utilisateur.
         3. Consulter ma mémoire et me connaitre. 
         4. Repondre au requette de l'utilisateur. 
         Important: Repondre uniquement par 1 ou 2 ou 3 ou 4" 

     - Réponse de l'agent au prompt envoyée: 3

     - Mémorisation du choix pour l'apprentissage des patternes.

     - Prompt Envoyée à l'agent:
         "Vous avez choisi l'action de base Consulter ma mémoire et me connaitre. 
         Voici la liste d'action génerale à ce choix possible .
         1. Connaitre mon identité. 
         2. Connaitre mes traites. 
         3. Connaitre mon environnement/mes capacitées.
         4. Consulter ma mémoire. 
         5. Repondre au requette de l'utilisateur. 
         6. Revenir au choix des informations de base.
         Important: Repondre uniquement par 1 ou 2 ou 3 ou 4 ou 5 ou 6" 

     - Réponse de l'agent au prompt envoyée: 1

     - Mémorisation du choix pour l'apprentissage des patternes.

     - Prompt Envoyée à l'agent:
         "Vous avez choisi l'action génerale Connaitre mon identité. 
         Voici la liste d'action spécifique à ce choix possible.
         1. Consulter les n dernière identités?
         2. Consulter un identité en particulier?
         3. Voir tout les identités?
         4. Repondre au requette de l'utilisateur?
         5. Revenir au choix des informations génerale.
         Important: Repondre uniquement par 1 ou 2 ou 3 ou 4 ou 5" 

     - Réponse de l'agent au prompt envoyée: 3

     - Mémorisation du choix pour l'apprentissage des patternes.

     - Prompt Envoyée à l'agent:
         "Vous avez choisi l'action spécifique Voir tout les identités.
         Voici tout les identités:
         - Identité 1: "...."
         - Identité 2: "..."
         ...
         - Identité n: "..."
         Voici la liste d'action spécifique après ce choix possible.
         1. Consulter les n dernière identités?
         2. Consulter un identité en particulier?
         3. Voir tout les identités?
         4. Repondre au requette de l'utilisateur?
         5. Revenir au choix des informations génerale.
         Important: Repondre uniquement par 1 ou 2 ou 3 ou 4 ou 5" 

     - Réponse de l'agent au prompt envoyée: 5

     - Mémorisation du choix pour l'apprentissage des patternes.

     - Prompt Envoyée à l'agent:
         "Vous avez choisi l'action spécifique Revenir au choix des informations génerale. 
         Voici la liste d'action génerale possible.
         1. Connaitre mon identité. 
         2. Connaitre mes traits. 
         3. Connaitre mon environnement/mes capacitées.
         4. Consulter ma mémoire. 
         5. Repondre au requette de l'utilisateur. 
         6. Revenir au choix des informations de base.
         Important: Repondre uniquement par 1 ou 2 ou 3 ou 4 ou 5 ou 6" 

     - Réponse de l'agent au prompt envoyée: 2

     - Mémorisation du choix pour l'apprentissage des patternes.

     - Prompt Envoyée à l'agent:
         "Vous avez choisi l'action spécifique Consulter mes traits. 
         Voici la liste d'action spécifique après ce choix possible.
         1. Consulter les n dernière traits?
         2. Consulter un trait en particulier?
         3. Voir tout les traits?
         4. Repondre au requette de l'utilisateur?
         5. Revenir au choix des informations génerale.
         Important: Repondre uniquement par 1 ou 2 ou 3 ou 4 ou 5" 

     - Réponse de l'agent au prompt envoyée: 1

     - Mémorisation du choix pour l'apprentissage des patternes.

     - Prompt Envoyée à l'agent:
         "Vous avez choisi l'action spécifique Consulter les n dernière traits. 
         Veuillez entrer le nombre "n":
         Important: Repondre uniquement en nombre entier"

     - Réponse de l'agent au prompt envoyée: 3

     - Mémorisation du choix pour l'apprentissage des patternes.

     - Prompt Envoyée à l'agent:
         "Vous avez choisi l'action spécifique Consulter les 3 derniers traits.
         Voici les 3 dernières traits:
         - Trait 1: "...."
         - Trait 2: "..."
         - Trait 3: "..."
         Voici la liste d'action spécifique après ce choix possible.
         1. Consulter les n dernière traits?
         2. Consulter un trait en particulier?
         3. Voir tout les traits?
         4. Repondre au requette de l'utilisateur?
         5. Revenir au choix des informations génerale.
         Important: Repondre uniquement par 1 ou 2 ou 3 ou 4 ou 5" 

     - Réponse de l'agent au prompt envoyée: 4

     - Mémorisation du choix pour l'apprentissage des patternes.

     - Prompt Envoyée à l'agent:
         "Vous avez choisi l'action spécifique Repondre au requette de l'utilisateur. 
         Voici la requette de l'utilisateur: "Qui es-tu ?"

     - Réponse de l'agent au prompt envoyée: "Réponse"

     -  Mémorisation du choix pour l'apprentissage des patternes.
     -  Apprentissage de patternes

     - Delivrance de la réponse à l'utilisateur: "Réponse"

