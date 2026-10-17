/* MiniVid UI language switcher. French is the original/default language. */
(() => {
  const en = {
    "Lectures": "Viewing history", "Panneau": "Panel", "Masqué": "Hidden", "En cours": "In progress", "Dernières lectures": "Recently watched", "En cours et récentes": "In progress and recent", "Aucune lecture à afficher.": "No viewing history to display.",
    "GESTION": "MANAGEMENT",
    "GÉRER LA BIBLIOTHÈQUE": "MANAGE YOUR LIBRARY",
    "L’ESSENTIEL EN UN COUP D’ŒIL": "AT A GLANCE",
    "← Bibliothèque": "← Library",
    "Une bibliothèque à jour, des réglages à portée de main.": "Keep your library current and your settings within reach.",
    "Voir le stockage": "View storage",
    "Sources et clients": "Sources and clients",
    "Préférences": "Preferences",
    "Activité": "Activity",
    "Entretenir la bibliothèque": "Maintain your library",
    "Actualisez l’index ou renouvelez les aperçus de vos vidéos.": "Update the index or refresh your video previews.",
    "Actualiser les vidéos": "Refresh videos",
    "Retrouvez les nouveaux fichiers et mettez à jour les informations de la bibliothèque.": "Find new files and update library information.",
    "Renouveler les miniatures": "Refresh thumbnails",
    "Videz le cache des images. Les miniatures seront recréées à la prochaine consultation.": "Clear the image cache. Thumbnails will be recreated when next viewed.",
    "Les fichiers vidéo sont conservés.": "Video files are kept.",
    "Sources et clients BitTorrent": "Sources and BitTorrent clients",
    "Connectez vos clients et choisissez comment gérer chaque source.": "Connect your clients and choose how each source is managed.",
    "Connexions et autorisations": "Connections and permissions",
    "Clients, dossiers et droits de suppression": "Clients, folders and deletion permissions",
    "Liaison BitTorrent": "BitTorrent connection",
    "Afficher les statistiques du torrent associé.": "Show statistics for the associated torrent.",
    "Suppression des vidéos": "Video deletion",
    "Chaque source conserve son propre mode de suppression.": "Each source keeps its own deletion mode.",
    "Clients connectés": "Connected clients",
    "+ Ajouter un client": "+ Add client",
    "Aucun client connecté. Ajoutez un client pour afficher les informations BitTorrent.": "No connected clients. Add a client to display BitTorrent information.",
    "Préférences de lecture": "Playback preferences",
    "Personnalisez les suggestions de votre bibliothèque.": "Customize suggestions from your library.",
    "Des suggestions locales à partir des tags en commun.": "Local suggestions based on shared tags.",
    "Afficher les vidéos similaires": "Show similar videos",
    "Sur la page de lecture, à côté de la vidéo.": "Beside the video on the playback page.",
    "Tags en commun au minimum": "Minimum shared tags",
    "Activité récente": "Recent activity",
    "Le suivi des opérations de votre bibliothèque.": "Track library operations.",
    "Journal": "Activity log",
    "Environnement de test": "Test environment",
    "Les vidéos restent en lecture seule.": "Videos remain read only.",
    "Votre bibliothèque": "Your library",
    "Vos fichiers, vos décisions.": "Your files, your decisions.",
    "Visualisez l’espace utilisé. Repérez les copies inutiles.": "See used space and find unnecessary copies.",
    "ESPACE DU VOLUME": "VOLUME SPACE",
    "VIDÉOS INDEXÉES": "INDEXED VIDEOS",
    "GAIN ESTIMÉ": "ESTIMATED SAVINGS",
    "Chaque volume est compté une seule fois.": "Each volume is counted once.",
    "Source": "Source",
    "Détails des sources": "Source details",
    "Règles de nettoyage": "Cleanup rules",
    "Doublons vérifiés": "Verified duplicates",
    "Même contenu · fichiers distincts": "Same content · separate files",
    "Comparez les copies": "Compare copies",
    "Choisissez celle à garder": "Choose one to keep",
    "Supprimez le surplus": "Delete extra copies",
    "Seules les copies au contenu identique sont proposées. Les liens physiques ne comptent pas comme des doublons. Le gain d’espace est estimé.": "Only copies with identical content are suggested. Hardlinks are not counted as duplicates. Space savings are estimated.",
    "Liens physiques et cross-seed": "Hardlinks and cross-seed",
    "Aucune copie supplémentaire": "No additional copies",
    "Vos fichiers": "Your files",
    "Vos règles de nettoyage": "Your cleanup rules",
    "Définissez les conditions. L’activation reste une décision séparée.": "Set conditions. Activation remains a separate decision.",

    "Apparence": "Appearance", "Personnaliser le thème": "Customize theme",
    "Thème": "Theme", "Sombre": "Dark", "Clair": "Light", "Bleu nuit": "Midnight",
    "Forêt": "Forest", "Personnalisé": "Custom", "Couleur principale": "Accent color",
    "Fond personnalisé": "Custom background", "Thème enregistré": "Theme saved",
    "Fichier et téléchargement": "File and download", "Que faire de cette vidéo ?": "What should happen to this video?",
    "Conditions du nettoyage": "Cleanup conditions", "Réglages du nettoyage automatique": "Automatic cleanup settings",
    "L’espace utilisé, les doublons et vos fichiers.": "Used space, duplicates and your files.",
    "Les doublons et les fichiers suivent la source sélectionnée.": "Duplicates and files follow the selected source.",
    "TEST · lecture seule": "TEST · read only", "Actualisation des fichiers…": "Updating files…",

    "Stockage": "Storage", "← Retour": "← Back", "Ouvrir la page Stockage": "Open Storage",
    "Trier, examiner et protéger vos vidéos avant de libérer de la place.": "Sort, review and protect videos before freeing space.",
    "Analyser les doublons": "Scan for duplicates", "Copies vérifiées": "Verified copies", "Liens vers un même fichier physique": "Links to the same physical file",
    "Afficher": "Show", "Tous": "All", "Jamais lancés": "Never started", "Arrêtés avant 30 %": "Stopped before 30%", "Candidats": "Candidates", "Protégés": "Protected",
    "Taille décroissante": "Largest first", "Plus anciens fichiers": "Oldest file dates", "Détectés le plus tôt": "First detected", "Dernier visionnage le plus ancien": "Oldest viewing date", "Nombre de démarrages": "Playback starts", "Progression maximale": "Highest reached position",
    "Vidéo": "Video", "Fichier du": "File dated", "Lectures": "Plays", "Max.": "Max.", "Dernière fois": "Last played", "Décision": "Decision",
    "Candidat au nettoyage": "Cleanup candidate", "Conserver sans règle": "Keep without a rule", "Protéger définitivement": "Protect", "Autoriser le nettoyage": "Allow cleanup",
    "Ratio minimum": "Minimum ratio", "Temps de seed minimum (jours)": "Minimum seeding time (days)", "Condition": "Condition", "Ratio ET durée": "Ratio AND time", "Ratio OU durée": "Ratio OR time",
    "Déclencher": "Trigger", "Lorsque le stockage manque de place": "When storage is low", "Dès que les conditions sont atteintes": "As soon as conditions are met",
    "Démarrer si l’espace libre passe sous (%)": "Start when free space drops below (%)", "Arrêter une fois l’espace libre remonté à (%)": "Stop once free space reaches (%)", "Enregistrer la décision": "Save decision",
    "Exemple : sous 15 % libres, MiniVid nettoie les candidats éligibles jusqu’à retrouver 20 % libres.": "Example: below 15% free, MiniVid cleans eligible candidates until free space reaches 20%.",
    "La règle par défaut des nouveaux candidats se configure sur": "Configure the default rule for new candidates on", "Modifier ce défaut ne change pas les décisions déjà enregistrées.": "Changing this default does not alter existing decisions.",
    "Affichage : liste": "View: list", "Affichage : vignettes": "View: thumbnails", "Largeur : standard": "Width: standard", "Largeur : large": "Width: wide", "Largeur : plein écran": "Width: full", "Changer l'affichage": "Change view", "Changer la largeur": "Change width",
    "Nettoyage automatique": "Automatic cleanup", "Autoriser le nettoyage automatique": "Allow automatic cleanup", "Propriétaire": "Owner", "Définir cette instance": "Use this instance", "Identifiant d’instance": "Instance ID",
    "Désactivé par défaut. L’activation exige une synchronisation configurée et une seule instance propriétaire. La file reste consultable ci-dessous.": "Off by default. Activation requires configured synchronization and one owner instance. The queue remains visible below.",
    "Règle par défaut des nouveaux candidats": "Default rule for new candidates", "Appliquée lorsque vous choisissez « Autoriser le nettoyage » pour une nouvelle vidéo. Les règles déjà enregistrées ne changent pas. L'automatisation reste désactivée tant que vous ne l'activez pas séparément.": "Applied when you choose Allow cleanup for a new video. Existing rules do not change. Automation remains off until separately enabled.",
    "Enregistrer la règle par défaut": "Save default rule", "Fichiers": "Files", "Sélectionner la page": "Select page", "Effacer la sélection": "Clear selection", "Examiner la suppression…": "Review deletion…", "Sélection": "Selection", "Sélectionner": "Select", "Sélectionner ce média": "Select this video", "Supprimer…": "Delete…",
    "Examiner la sélection": "Review selection", "Confirmation": "Confirmation", "Annuler": "Cancel", "Supprimer définitivement": "Delete permanently", "Dernière lecture :": "Last played:", "Fédération :": "Federation:",
    "Supprimer les autres copies": "Delete other copies", "Aucune copie physique vérifiée.": "No verified physical copies.",
    "Aucun lien physique partagé dans les sources.": "No shared physical link within the sources.",
    "Lancez une analyse pour vérifier les copies.": "Run a scan to verify copies.", "Analyse à lancer.": "Scan required.",
    "MiniVid ne supprime automatiquement que les vidéos autorisées ici, une fois les conditions de chaque torrent atteintes.": "MiniVid only deletes videos explicitly authorized here after all torrent conditions are met.",
    "Les copies sont vérifiées par SHA‑256. Les liens physiques et torrents cross-seed ne comptent pas comme plusieurs fichiers. La place indiquée reste une estimation sur les volumes avec snapshots ou reflinks.": "Copies are verified with SHA-256. Hardlinks and cross-seed torrents are not counted as separate files. Reclaimable space is an estimate on volumes with snapshots or reflinks.",
    "Accueil MiniVid": "MiniVid home", "Rechercher une vidéo, un dossier...": "Search a video or folder...",
    "Tri": "Sort", "Récentes": "Newest", "Nom": "Name", "Taille": "Size", "Résolution ↓": "Resolution ↓", "Résolution ↑": "Resolution ↑",
    "Non lues": "Unwatched", "Jamais lues": "Never watched", "Lues": "Watched", "Affichage": "Display", "Toutes": "All", "Tout": "All",
    "Par page": "Per page", "Mélange": "Order", "Dossiers d'abord": "Folders first", "Vidéos d'abord": "Videos first",
    "Vignettes": "Thumbnails", "Compact": "Compact", "Confort": "Comfortable", "Large": "Large", "Grouper par période": "Group by period",
    "Groupes": "Groups", "Favoris": "Favorites", "Collections": "Collections", "Thème clair/sombre": "Light/dark theme",
    "Maintenance": "Maintenance", "Déconnexion": "Log out", "← Parent": "← Parent", "Global": "All sources",
    "Afficher ou masquer les tags": "Show or hide tags", "Tags populaires": "Popular tags", "Masquer": "Hide", "Aucun tag": "No tags",
    "Tags sélectionnés": "Selected tags", "← Précédent": "← Previous", "Suivant →": "Next →", "Haut de page": "Back to top",
    "Aperçu vidéo": "Video preview", "Aperçu dossier": "Folder preview", "Sans tag": "No tags", "Lue": "Watched", "Non lue": "Unwatched",
    "VIDÉO": "VIDEO", "DOSSIER": "FOLDER", "Dernière modif.": "Last modified", "Aucun élément.": "No items.",
    "Utilisateur": "Username", "Mot de passe": "Password", "Se souvenir de moi": "Remember me", "Connexion": "Log in", "Entrer": "Enter",
    "Authentification désactivée. Définissez": "Authentication is disabled. Set", "pour l'activer.": "to enable it.",
    "Retour à la liste": "Back to library", "Retour": "Back", "Ce fichier vidéo est incomplet ou endommagé.": "This video file is incomplete or damaged.",
    "MiniVid a arrêté la lecture avant qu'elle ne boucle indéfiniment. Vérifiez ou retéléchargez le fichier source.": "MiniVid stopped playback before it could loop indefinitely. Check or download the source file again.",
    "Télécharger le fichier": "Download file", "Ce navigateur ne peut pas lire directement ce fichier .": "This browser cannot play this .",
    "et le transcodage est désactivé.": " file directly and transcoding is disabled.",
    "Activez": "Enable", "pour autoriser le remux/transcodage à la volée, ou utilisez un navigateur Chromium.": "to allow live remuxing/transcoding, or use a Chromium browser.",
    "Zoom": "Zoom", "Résolution :": "Resolution:", "+ Tag": "+ Tag", "Favori": "Favorite", "Marquer non lue": "Mark unwatched",
    "Marquer lue": "Mark watched", "Fichier et partage": "File and sharing", "Supprimer la vidéo": "Delete video", "Vidéos similaires": "Similar videos",
    "Raccourcis": "Shortcuts", "Lecture/Pause": "Play/Pause", "Reculer 10s": "Back 10s", "Avancer 10s": "Forward 10s", "Volume": "Volume",
    "Plein écran": "Fullscreen", "Muet": "Mute", "Indexation, cache et options partagées.": "Indexing, cache and shared options.",
    "Actions": "Actions", "Rescan complet": "Full rescan", "Purger miniatures": "Clear thumbnails", "Prêt.": "Ready.",
    "Journal récent": "Recent log", "Page précédente": "Previous page", "Précédent": "Previous", "Page suivante": "Next page", "Suivant": "Next", "Chargement...": "Loading...",
    "Affiche sous chaque vidéo une grille de contenus ayant des tags en commun. Ce réglage est stocké côté serveur.": "Shows a grid of videos sharing tags below each video. This setting is stored on the server.",
    "Activer": "Enable", "Enregistrer": "Save", "Sources vidéo et clients BitTorrent": "Video sources and BitTorrent clients",
    "Associez un client à une ou plusieurs sources pour afficher les statistiques du torrent. La suppression reste contrôlée par une option globale et un mode propre à chaque source.": "Associate a client with one or more sources to show torrent statistics. Deletion remains controlled by a global option and a setting for each source.",
    "Activer la liaison BitTorrent": "Enable BitTorrent integration", "Autoriser la suppression": "Allow deletion", "Clients": "Clients", "Ajouter un client": "Add client",
    "Association des sources": "Source association", "Enregistrer la configuration": "Save configuration", "Nom": "Name", "Type": "Type", "URL": "URL",
    "Liens du projet": "Project links", "MiniVid sur GitHub": "MiniVid on GitHub", "PornScout sur GitHub": "PornScout on GitHub",
    "Tester": "Test", "Retirer": "Remove", "Aucun client": "No client", "Chemin vu par le client": "Path seen by the client", "Suppression": "Deletion",
    "Désactivée": "Disabled", "Fichier uniquement": "File only", "Torrent et données": "Torrent and data", "Conservé si vide": "Kept if empty",
    "Démarrage du scan...": "Starting scan...", "Journal en direct...": "Live log...", "Mise à jour du journal...": "Updating log...", "Aucun événement": "No events",
    "Aucun journal": "No log", "Activé": "Enabled", "Désactivé": "Disabled", "Configuration enregistrée.": "Configuration saved.",
    "Test en cours...": "Test in progress...", "Connexion réussie": "Connection successful", "Enregistrement...": "Saving...", "Liaison active": "Integration enabled", "Liaison inactive": "Integration disabled",
    "Date": "Date", "Action": "Action", "Fichiers": "Files", "Modifiés": "Changed", "Durée": "Duration",
    "Ajouter des tags séparés par des virgules :": "Add comma-separated tags:", "Erreur tag": "Tag error", "Erreur favori": "Favorite error",
    "Erreur état de lecture": "Playback-state error", "Ouvrir": "Open", "le client BitTorrent": "the BitTorrent client",
    "Client BitTorrent :": "BitTorrent client:", "Gestion indisponible :": "Management unavailable:", "Confirmez la suppression": "Confirm deletion",
    "Supprimer la vidéo": "Delete video", "Suppression en cours...": "Deleting...", "Suppression refusée :": "Deletion refused:",
    "Cliquez une seconde fois pour effacer définitivement le fichier.": "Click a second time to permanently delete the file.",
    "Cliquez une seconde fois pour retirer": "Click a second time to remove", "torrent(s) et effacer leurs données.": "torrent(s) and delete their data.",
    "Attention : cette vidéo est dans vos favoris.": "Warning: this video is in your favorites.", "Supprimer le favori": "Delete favorite",
    "Démarrage...": "Starting...", "Scan complet en cours…": "Full scan in progress...", "Scan terminé": "Scan complete",
    "Erreur :": "Error:", "Erreur réseau :": "Network error:", "Erreur réseau purge :": "Thumbnail-clear network error:",
    "Miniatures supprimées :": "Thumbnails removed:", "Aucun journal": "No log", "Statut :": "Status:", "Scan en cours": "Scan in progress",
    "Configuration indisponible :": "Configuration unavailable:", "Configuration enregistrée. Enregistrez avant de tester un nouveau client.": "Configuration saved. Save before testing a new client."
  };

  const translateText = value => {
    const match = value.match(/^(\s*)(.*?)(\s*)$/s);
    const translated = en[match[2]];
    if (translated) return match[1] + translated + match[3];
    for (const [french, english] of Object.entries(en)) {
      if (match[2].startsWith(french + ' ')) return match[1] + english + match[2].slice(french.length) + match[3];
    }
    return value;
  };
  function translate(root = document.body) {
    const enabled = document.documentElement.lang === 'en';
    document.querySelectorAll('[data-i18n-original]').forEach(el => {
      if (!enabled) el.textContent = el.dataset.i18nOriginal;
    });
    if (!enabled) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    nodes.forEach(node => { const replacement = translateText(node.nodeValue); if (replacement !== node.nodeValue) node.nodeValue = replacement; });
    root.querySelectorAll?.('[title], [aria-label], [placeholder]').forEach(el => {
      ['title', 'aria-label', 'placeholder'].forEach(attr => {
        const value = el.getAttribute(attr); const replacement = value && en[value];
        if (replacement) el.setAttribute(attr, replacement);
      });
    });
  }

  async function setLanguage(lang) {
    document.documentElement.lang = lang;
    localStorage.setItem('minivid_lang', lang);
    document.querySelectorAll('.language-switcher button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.lang === lang)));
    if (lang === 'en') translate(); else window.location.reload();
    try { await fetch('/api/preferences', { method: 'POST', credentials: 'same-origin', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({lang}) }); } catch (_) {}
  }

  function mountSwitcher() {
    const host = document.querySelector('.header-right');
    if (!host || host.querySelector('.language-switcher')) return;
    const switcher = document.createElement('div');
    switcher.className = 'language-switcher';
    switcher.setAttribute('aria-label', 'Language / Langue');
    switcher.innerHTML = '<button type="button" data-lang="fr" title="Français" aria-label="Français">🇫🇷</button><button type="button" data-lang="en" title="English" aria-label="English">🇬🇧</button>';
    switcher.querySelectorAll('button').forEach(button => button.addEventListener('click', () => setLanguage(button.dataset.lang)));
    switcher.querySelectorAll('button').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.lang === document.documentElement.lang)));
    host.prepend(switcher);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const stored = localStorage.getItem('minivid_lang');
    if (stored === 'en' || stored === 'fr') document.documentElement.lang = stored;
    mountSwitcher(); translate();
    new MutationObserver(records => { if (document.documentElement.lang === 'en') records.forEach(record => record.addedNodes.forEach(node => {
      if (node.nodeType === Node.ELEMENT_NODE) translate(node);
      if (node.nodeType === Node.TEXT_NODE) node.nodeValue = translateText(node.nodeValue);
    })); }).observe(document.body, {childList: true, subtree: true});
  });
})();
