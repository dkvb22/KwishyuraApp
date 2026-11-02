# -*- coding: utf-8 -*-
"""
Kwishyura — the ONE translation table for the whole application.

Every user-facing string lives here as (key, Kinyarwanda, English, French).
Because each key carries all three languages on one row, a key can never be
missing from one language.  The same table is used by:
  * the server (Jinja templates, flash messages, error pages, CSV export), and
  * the browser (static/i18n.js receives this table, so switching language is
    instant and needs no page reload).

Placeholders use {name} syntax and are filled with the same parameters on the
server and in the browser.  Strings that contain <strong> are rendered with
data-i18n-html (parameters are HTML-escaped first).
"""

DEFAULT_LANG = 'rw'          # Kinyarwanda is the primary language
LANGS = ('rw', 'en', 'fr')

_ROWS = [
# ── Common / layout ─────────────────────────────────────────────────────────
('page_title', "Kwishyura | Icyizere mu Kugura no Kwishyura", "Kwishyura | Trust in Every Transaction", "Kwishyura | La confiance dans chaque transaction"),
('brand_sub', "ICYIZERE MU KUGURA NO KWISHYURA", "TRUST IN EVERY TRANSACTION", "LA CONFIANCE DANS CHAQUE TRANSACTION"),
('logout', "Sohoka", "Log out", "Se déconnecter"),
('nav_settings', "Igenamiterere", "Settings", "Paramètres"),
('lang_label', "Ururimi", "Language", "Langue"),
('theme_toggle', "Hindura isura", "Toggle theme", "Changer de thème"),
('footer_text', "© Kwishyura · Verisiyo y'igerageza · MoMo na SMS ni iz'igerageza, si serivisi nyazo.", "© Kwishyura · Local testing build · MoMo and SMS are simulations, not real services.", "© Kwishyura · Version de test locale · MoMo et SMS sont des simulations, pas de vrais services."),
('btn_cancel', "Reka", "Cancel", "Annuler"),
('btn_submit', "Ohereza", "Submit", "Soumettre"),
('role_shopkeeper', "Nyir'iduka", "Shopkeeper", "Commerçant"),
('role_customer', "Umukiriya", "Customer", "Client"),

# ── Sign in / register ──────────────────────────────────────────────────────
('auth_create_title', "Fungura konti", "Create an account", "Créer un compte"),
('auth_login_title', "Murakaza neza", "Welcome back", "Bon retour"),
('auth_subtitle', "Gucunga inguzanyo z'iduka ryawe mu buryo bworoshye kandi bwizewe.", "Manage shop credit with clarity and trust.", "Gérez le crédit de votre boutique avec clarté et confiance."),
('label_fullname', "Amazina yuzuye", "Full name", "Nom complet"),
('label_account_type', "Ubwoko bwa konti", "Account type", "Type de compte"),
('label_shopname', "Izina ry'iduka (ku banyiri iduka gusa)", "Shop name (shopkeepers only)", "Nom de la boutique (commerçants uniquement)"),
('placeholder_shopname', "Izina ry'iduka", "Shop name", "Nom de la boutique"),
('label_phone', "Numero ya telefoni", "Phone number", "Numéro de téléphone"),
('label_password', "Ijambo ry'ibanga", "Password", "Mot de passe"),
('btn_register', "Iyandikishe", "Register", "S'inscrire"),
('btn_signin', "Injira", "Sign in", "Se connecter"),
('already_registered', "Usanzwe ufite konti? ", "Already registered? ", "Déjà inscrit ? "),
('signin_link', "Injira", "Sign in", "Se connecter"),
('new_here', "Uri mushya hano? ", "New here? ", "Nouveau ici ? "),
('create_account_link', "Fungura konti", "Create account", "Créer un compte"),
('aside_title', "Icyizere mu Kugura no Kwishyura.", "Trust in Every Transaction.", "La confiance dans chaque transaction."),
('aside_body', "Kurikirana inguzanyo, ubone imyenda isigaye, kandi ubike inyandiko z'ibyishyuwe zizewe.", "Track credit sales, see outstanding balances, and keep an auditable record of repayments.", "Suivez les ventes à crédit, consultez les soldes impayés et conservez un historique vérifiable des remboursements."),
('aside_focus', "Rwanda · RWF", "Rwanda-focused · RWF", "Axé sur le Rwanda · RWF"),

# ── Shopkeeper dashboard: header & summary ──────────────────────────────────
('sk_eyebrow', "IKIBAHO CY'IDUKA", "SHOPKEEPER DASHBOARD", "TABLEAU DE BORD COMMERÇANT"),
('sk_code_hint', "Sangiza iyi code abakiriya biyandikishije kugira ngo bahuze konti zabo n'iduka ryawe mu buryo bwizewe: ", "Share this code with registered customers so they can securely link their account: ", "Partagez ce code avec les clients inscrits pour qu'ils puissent lier leur compte en toute sécurité : "),
('sk_code_label', "Code y'iduka", "Shop Code", "Code boutique"),
('btn_export_csv', "Kuramo CSV", "Export CSV", "Exporter en CSV"),
('metric_outstanding', "Umwenda usigaye", "Outstanding credit", "Crédit en cours"),
('metric_total_sales', "Inguzanyo zose", "Total credit sales", "Total des ventes à crédit"),
('metric_total_payments', "Ibyishyuwe", "Total repaid", "Total remboursé"),
('metric_customers', "Abakiriya bahujwe", "Linked customers", "Clients liés"),
('metric_in_debt', "bafite umwenda", "in debt", "endettés"),
('metric_entries', "Ibyanditswe", "Ledger entries", "Écritures du registre"),

# ── Chart ───────────────────────────────────────────────────────────────────
('chart_title', "Incamake y'imyenda", "Balance Overview", "Aperçu des soldes"),
('chart_subtitle', "Uko imyenda n'ibyishyuwe byagiye bihinduka uko iminsi ishira", "Debt and repayment trends over time", "Évolution des dettes et des remboursements dans le temps"),
('period_all', "Byose", "All", "Tout"),
('period_month', "Uku kwezi", "This month", "Ce mois"),
('period_week', "Iki cyumweru", "This week", "Cette semaine"),
('period_day', "Uyu munsi", "Today", "Aujourd'hui"),
('chart_tab_trend', "Imiterere", "Trend", "Tendance"),
('chart_tab_customers', "Abakiriya", "By Customer", "Par client"),
('chart_no_data', "Nta makuru ahari. Banza wandike inguzanyo kugira ngo ubone igishushanyo.", "No data yet. Record a credit sale to see the chart.", "Aucune donnée. Enregistrez une vente à crédit pour voir le graphique."),

# ── Customers with debt ─────────────────────────────────────────────────────
('panel_outstanding', "Abakiriya bafite imyenda", "Customers with outstanding balances", "Clients avec des soldes impayés"),
('th_customer', "Umukiriya", "Customer", "Client"),
('th_phone', "Telefoni", "Phone", "Téléphone"),
('th_total_credit', "Inguzanyo zose", "Total credit", "Crédit total"),
('th_paid', "Ibyishyuwe", "Repaid", "Remboursé"),
('th_outstanding', "Isigaye", "Outstanding", "Restant"),
('th_progress', "Aho kwishyura bigeze", "Repayment progress", "Progression du remboursement"),
('th_reminder', "Ubwibutso", "Reminder", "Rappel"),
('btn_simulate_sms', "Ohereza SMS y'igerageza", "Simulate SMS", "Simuler un SMS"),

# ── Record credit sale ──────────────────────────────────────────────────────
('panel_record_sale', "Andika inguzanyo", "Record credit sale", "Enregistrer une vente à crédit"),
('label_customer', "Umukiriya", "Customer", "Client"),
('label_products', "Ibicuruzwa", "Products", "Produits"),
('btn_add_line', "+ Ongeraho", "+ Add", "+ Ajouter"),
('label_total', "Igiteranyo:", "Total:", "Total :"),
('label_due_date', "Itariki yo kwishyura", "Due date", "Date d'échéance"),
('label_notes', "Ibisobanuro (si ngombwa)", "Notes (optional)", "Notes (facultatif)"),
('placeholder_notes', "Andika andi makuru...", "Add any extra details...", "Ajoutez des détails..."),
('btn_save_sale', "Bika inguzanyo", "Save credit sale", "Enregistrer la vente"),
('li_product', "Igicuruzwa", "Product", "Produit"),
('li_qty', "Ingano", "Quantity", "Quantité"),
('li_price', "Igiciro (RWF)", "Price (RWF)", "Prix (RWF)"),
('li_subtotal', "Igiteranyo cy'igicuruzwa", "Subtotal", "Sous-total"),
('select_product', "— Hitamo igicuruzwa —", "— Select a product —", "— Choisissez un produit —"),
('item_default', "Igicuruzwa", "Item", "Article"),
('alert_min_one_line', "Ugomba kugira nibura igicuruzwa kimwe.", "You need at least one product line.", "Il faut au moins une ligne de produit."),

# ── Repayment / find customer ───────────────────────────────────────────────
('panel_repay', "Andika ubwishyu bw'amafaranga mu ntoki", "Record cash repayment", "Enregistrer un remboursement en espèces"),
('label_amount', "Amafaranga (RWF)", "Amount (RWF)", "Montant (RWF)"),
('btn_confirm_repay', "Emeza ubwishyu", "Confirm cash repayment", "Confirmer le remboursement"),
('panel_find_customer', "Shakisha umukiriya", "Find customer", "Trouver un client"),
('label_cust_phone', "Telefoni y'umukiriya wiyandikishije", "Registered customer's phone", "Téléphone du client inscrit"),
('btn_check_reg', "Reba niba yiyandikishije", "Check registration", "Vérifier l'inscription"),

# ── Products (shopkeeper) ───────────────────────────────────────────────────
('panel_products', "Ibicuruzwa byanjye", "My Products", "Mes produits"),
('btn_add_product', "Ongeraho igicuruzwa", "Add Product", "Ajouter un produit"),
('placeholder_search_product', "Shakisha igicuruzwa...", "Search products...", "Rechercher un produit..."),
('filter_all_categories', "Ubwoko bwose", "All categories", "Toutes les catégories"),
('stock_label', "Ibiri mu bubiko:", "Stock:", "Stock :"),
('btn_use', "Koresha", "Use", "Utiliser"),
('title_edit', "Hindura", "Edit", "Modifier"),
('title_toggle', "Hindura uko igicuruzwa gihagaze", "Toggle availability", "Changer la disponibilité"),
('title_delete', "Siba", "Delete", "Supprimer"),
('confirm_delete_product', "Wemeye gusiba igicuruzwa «{name}»?", "Delete product “{name}”?", "Supprimer le produit « {name} » ?"),
('products_empty_title', "Nta bicuruzwa bihari", "No products yet", "Aucun produit"),
('products_empty_desc', "Tangira wongera ibicuruzwa mu iduka ryawe.", "Start by adding products to your shop.", "Commencez par ajouter des produits à votre boutique."),

# Add / edit product modals
('modal_add_product', "Ongeraho igicuruzwa", "Add Product", "Ajouter un produit"),
('modal_edit_product', "Hindura igicuruzwa", "Edit Product", "Modifier le produit"),
('f_product_name', "Izina ry'igicuruzwa *", "Product name *", "Nom du produit *"),
('placeholder_product_name', "urugero: Imyumbati", "e.g. Cassava", "ex. : Manioc"),
('f_category', "Ubwoko", "Category", "Catégorie"),
('f_unit', "Igipimo cyo kugurisha *", "Selling unit *", "Unité de vente *"),
('f_price_per_unit', "Igiciro ku gipimo kimwe (RWF) *", "Price per unit (RWF) *", "Prix par unité (RWF) *"),
('f_stock', "Ibiri mu bubiko (si ngombwa)", "Stock (optional)", "Stock (facultatif)"),
('placeholder_stock', "urugero: 50", "e.g. 50", "ex. : 50"),
('f_status', "Uko bihagaze", "Status", "Statut"),
('f_description', "Ibisobanuro (si ngombwa)", "Description (optional)", "Description (facultatif)"),
('f_name_short', "Izina *", "Name *", "Nom *"),
('f_unit_short', "Igipimo *", "Unit *", "Unité *"),
('f_price_short', "Igiciro (RWF) *", "Price (RWF) *", "Prix (RWF) *"),
('f_stock_short', "Ibiri mu bubiko", "Stock", "Stock"),
('f_description_short', "Ibisobanuro", "Description", "Description"),
('btn_save_changes', "Bika impinduka", "Save Changes", "Enregistrer les modifications"),

# Product categories (stored values stay in English; only the label is translated)
('cat_food_groceries', "Ibiribwa n'ibicuruzwa by'ibanze", "Food & Groceries", "Alimentation et épicerie"),
('cat_beverages', "Ibinyobwa", "Beverages", "Boissons"),
('cat_household', "Ibikoresho byo mu rugo", "Household", "Articles ménagers"),
('cat_personal_care', "Isuku n'ubwiza", "Personal Care", "Soins personnels"),
('cat_vegetables_fruits', "Imboga n'imbuto", "Vegetables & Fruits", "Légumes et fruits"),
('cat_dairy', "Ibikomoka ku mata", "Dairy", "Produits laitiers"),
('cat_grains_cereals', "Ibinyampeke", "Grains & Cereals", "Grains et céréales"),
('cat_other', "Ibindi", "Other", "Autre"),

# Selling units
('unit_pcs', "ibice", "pcs", "pièces"),
('unit_kg', "kg", "kg", "kg"),
('unit_g', "g", "g", "g"),
('unit_l', "L", "L", "L"),
('unit_ml', "ml", "ml", "ml"),
('unit_packet', "paki", "packet", "paquet"),
('unit_bottle', "icupa", "bottle", "bouteille"),
('unit_box', "agasanduku", "box", "boîte"),
('unit_other', "ibindi", "other", "autre"),

# Statuses
('status_available', "Birahari", "Available", "Disponible"),
('status_unavailable', "Ntibihari", "Unavailable", "Indisponible"),
('status_paid', "Yishyuwe", "Paid", "Payé"),
('status_unpaid', "Ntiyishyuwe", "Unpaid", "Impayé"),
('status_reversed', "Yasubijwe inyuma", "Reversed", "Annulé"),
('status_open', "Gifunguye", "Open", "Ouvert"),
('status_resolved', "Cyakemutse", "Resolved", "Résolu"),
('status_pending', "Gitegereje", "Pending", "En attente"),
('status_simulated_success', "Bwagenze neza (igerageza)", "Simulated success", "Succès simulé"),
('status_failed', "Bwanze", "Failed", "Échec"),
('status_simulated', "Igerageza", "Simulated", "Simulé"),
('balance_settled', "Byishyuwe", "Settled", "Réglé"),

# ── Ledger ──────────────────────────────────────────────────────────────────
('panel_ledger', "Igitabo cy'ibikorwa", "Transaction ledger", "Registre des transactions"),
('ledger_note', "Gusubiza inyuma igikorwa ntibisiba inyandiko ya mbere. Amafaranga yose ari mu RWF atagabanyijemo ibice.", "Reversals preserve the original record. Amounts are whole RWF.", "Les annulations conservent l'enregistrement d'origine. Montants en RWF entiers."),
('placeholder_search', "Shakisha...", "Search...", "Rechercher..."),
('filter_all_types', "Ubwoko bwose", "All types", "Tous les types"),
('filter_all_customers', "Abakiriya bose", "All customers", "Tous les clients"),
('th_ref', "Inomero", "Reference", "Référence"),
('th_type', "Ubwoko", "Type", "Type"),
('th_details', "Ibisobanuro", "Details", "Détails"),
('th_qty', "Ingano", "Qty", "Qté"),
('th_unit_price', "Igiciro/Igice", "Unit Price", "Prix unitaire"),
('th_amount', "Amafaranga", "Amount", "Montant"),
('th_date', "Itariki", "Date", "Date"),
('th_action', "Igikorwa", "Action", "Action"),
('kind_sale', "Inguzanyo", "Credit sale", "Vente à crédit"),
('kind_payment', "Ubwishyu", "Payment", "Paiement"),
('kind_reversal', "Gusubiza inyuma", "Reversal", "Annulation"),
('btn_reverse', "Subiza inyuma", "Reverse", "Annuler"),
('confirm_reverse', "Subiza inyuma igikorwa {ref}? Inyandiko ya mbere izabikwa.", "Reverse transaction {ref}? The original record will be kept.", "Annuler la transaction {ref} ? L'enregistrement d'origine sera conservé."),
('no_txns', "Nta bikorwa bihari.", "No transactions yet.", "Aucune transaction."),

# Ledger descriptions generated by the system (stored in English, shown translated)
('item_cash_repayment', "Ubwishyu bw'amafaranga mu ntoki", "Cash repayment", "Remboursement en espèces"),
('item_simulated_momo', "Ubwishyu bwa MoMo (igerageza)", "SIMULATED MoMo payment", "Paiement MoMo SIMULÉ"),
('item_reversal_of', "Gusubiza inyuma {ref}", "Reversal of {ref}", "Annulation de {ref}"),

# Ledger reset
('reset_title', "Gusiba inyandiko zose (Reset)", "Reset all records", "Réinitialiser tous les enregistrements"),
('reset_desc', "Ibi bisiba burundu inyandiko z'ibikorwa. Bisaba ko nta mwenda usigaye.", "This permanently clears transaction records. It requires that no balance is outstanding.", "Cela efface définitivement les transactions. Aucun solde ne doit rester impayé."),
('btn_reset', "Siba byose", "Reset all", "Tout effacer"),
('modal_reset_title', "Gusiba inyandiko zose?", "Reset all records?", "Réinitialiser tous les enregistrements ?"),
('modal_reset_warning', "Ibi bizasiba burundu inyandiko zose z'ibikorwa kandi ntizizagaruka. Ni byiza kubanza kuramo CSV.", "This will permanently remove all transaction records. This data cannot be recovered. We recommend exporting a CSV first.", "Cela supprimera définitivement toutes les transactions. Ces données ne pourront pas être récupérées. Nous recommandons d'exporter un CSV d'abord."),
('btn_export_before', "Banza ukuremo CSV", "Export CSV first", "Exporter d'abord le CSV"),
('modal_type_reset', "Andika <strong>RESET</strong> kugira ngo wemeze:", "Type <strong>RESET</strong> to confirm:", "Tapez <strong>RESET</strong> pour confirmer :"),
('label_your_password', "Ijambo ry'ibanga ryawe:", "Your password:", "Votre mot de passe :"),
('btn_confirm_reset', "Emeza gusiba", "Confirm reset", "Confirmer l'effacement"),

# ── SMS log / disputes ──────────────────────────────────────────────────────
('panel_sms_log', "Urutonde rwa SMS (iz'igerageza)", "Simulated SMS log (test)", "Journal des SMS simulés (test)"),
('no_reminders', "Nta bwibutso buhari.", "No reminders yet.", "Aucun rappel."),
('panel_disputes', "Ibirego by'abakiriya", "Customer disputes", "Litiges des clients"),
('no_disputes', "Nta birego bihari.", "No disputes.", "Aucun litige."),
('btn_resolve', "Emeza ko cyakemutse", "Resolve", "Marquer comme résolu"),
('notif_reminder', "Kwishyura: {name}, umwenda wawe usigaye ni {amount} RWF. Injira muri konti yawe uwurebe.", "Kwishyura: {name}, outstanding balance is {amount} RWF. Please sign in to review.", "Kwishyura : {name}, votre solde impayé est de {amount} RWF. Veuillez vous connecter pour le consulter."),

# ── Customer dashboard ──────────────────────────────────────────────────────
('cu_eyebrow', "IKIBAHO CY'UMUKIRIYA", "CUSTOMER DASHBOARD", "TABLEAU DE BORD CLIENT"),
('cu_greeting', "Muraho, ", "Hello, ", "Bonjour, "),
('cu_subtitle', "Inguzanyo wafashe, ibyo wishyuye n'imyenda isigaye.", "Your credit purchases, repayments, and outstanding balances.", "Vos achats à crédit, remboursements et soldes impayés."),
('metric_total_outstanding', "Umwenda wose usigaye", "Total outstanding", "Total impayé"),
('metric_linked_shops', "Amaduka wahujwe na yo", "Linked shops", "Boutiques liées"),
('metric_recorded_txns', "Ibikorwa byanditswe", "Recorded transactions", "Transactions enregistrées"),
('alert_outstanding', "Ufite umwenda usigaye wa <strong>{amount} RWF</strong>. Wishyure nyir'iduka.", "You have an outstanding balance of <strong>{amount} RWF</strong>. Please pay the shopkeeper.", "Vous avez un solde impayé de <strong>{amount} RWF</strong>. Veuillez régler auprès du commerçant."),
('panel_connect_shop', "Huza iduka", "Connect to a shop", "Se connecter à une boutique"),
('connect_hint', "Saba nyir'iduka code ye yihariye. Guhuza bisaba ko winjira muri konti yawe.", "Ask your shopkeeper for their unique code. Linking requires your own login.", "Demandez à votre commerçant son code unique. La liaison nécessite votre propre connexion."),
('label_shop_code', "Code y'iduka", "Shop code", "Code boutique"),
('placeholder_shop_code', "Code y'inyuguti 8", "8-character code", "Code à 8 caractères"),
('btn_link_shop', "Huza iduka", "Link shop", "Lier la boutique"),
('panel_momo', "Ishyura ukoresheje MoMo (igerageza)", "Pay with MoMo (simulation)", "Payer avec MoMo (simulation)"),
('warning_test', "Uburyo bw'igerageza gusa. Nta mafaranga azimurwa.", "Test mode only. No money will move.", "Mode test uniquement. Aucun argent ne sera transféré."),
('label_shop', "Iduka", "Shop", "Boutique"),
('btn_pay', "Kora ubwishyu bw'igerageza", "Create test payment", "Créer un paiement test"),
('panel_balances', "Umwenda wawe kuri buri duka", "Balances by shop", "Soldes par boutique"),
('th_shop', "Iduka", "Shop", "Boutique"),
('th_status', "Uko bihagaze", "Status", "Statut"),
('no_shops_yet', "Nta maduka urahuza na yo.", "No shops linked yet.", "Aucune boutique liée."),
('panel_shop_products', "Ibicuruzwa by'amaduka", "Shop Products", "Produits des boutiques"),
('products_count', "Ibicuruzwa {n}", "{n} products", "{n} produits"),
('placeholder_search_in_shop', "Shakisha muri {shop}...", "Search in {shop}...", "Rechercher dans {shop}..."),
('badge_available', "Birahari", "Available", "Disponible"),
('no_products_shop', "Nyir'iduka ntaragaragaza ibicuruzwa biboneka.", "The shopkeeper has not listed any available products yet.", "Le commerçant n'a pas encore listé de produits disponibles."),
('panel_history', "Amateka y'inguzanyo n'ubwishyu", "Purchase and repayment history", "Historique des achats et remboursements"),
('th_desc', "Ibisobanuro", "Description", "Description"),
('th_due', "Itariki yo kwishyura", "Due date", "Échéance"),
('th_dispute', "Ikirego", "Dispute", "Litige"),
('placeholder_dispute', "Sobanura ikibazo", "Describe issue", "Décrivez le problème"),
('no_txns_cu', "Nta bikorwa bihari.", "No transactions yet.", "Aucune transaction."),
('panel_test_payments', "Ubwishyu bw'igerageza", "Test payment attempts", "Tentatives de paiement test"),
('btn_simulate_success', "Emeza ko bwagenze neza", "Simulate success", "Simuler un succès"),
('btn_simulate_fail', "Emeza ko bwanze", "Simulate failure", "Simuler un échec"),
('no_payment_attempts', "Nta bwishyu bwigeragejwe.", "No payment attempts.", "Aucune tentative de paiement."),
('panel_reminders', "Ubwibutso", "Reminders", "Rappels"),
('no_reminders_cu', "Nta bwibutso buhari.", "No reminders yet.", "Aucun rappel."),
('panel_my_disputes', "Ibirego byanjye", "My disputes", "Mes litiges"),

# ── Settings ────────────────────────────────────────────────────────────────
('settings_eyebrow', "IGENAMITERERE", "SETTINGS", "PARAMÈTRES"),
('settings_title', "Igenamiterere rya konti", "Account Settings", "Paramètres du compte"),
('settings_subtitle', "Hindura amakuru yawe bwite kandi ucunge konti yawe.", "Update your personal information and manage your account.", "Mettez à jour vos informations personnelles et gérez votre compte."),
('back_dashboard', "Subira ku kibaho", "Back to Dashboard", "Retour au tableau de bord"),
('settings_profile', "Amakuru bwite", "Profile", "Profil"),
('settings_update_name', "Hindura izina", "Update Name", "Modifier le nom"),
('settings_update_email', "Hindura imeli", "Update Email", "Modifier l'e-mail"),
('settings_update_shopname', "Hindura izina ry'iduka", "Update Shop Name", "Modifier le nom de la boutique"),
('settings_security', "Umutekano", "Security", "Sécurité"),
('settings_update_password', "Hindura ijambo ry'ibanga", "Change Password", "Changer le mot de passe"),
('label_email', "Imeli", "Email", "E-mail"),
('placeholder_email', "urugero@email.com", "example@email.com", "exemple@email.com"),
('label_shopname_short', "Izina ry'iduka", "Shop Name", "Nom de la boutique"),
('label_current_password', "Ijambo ry'ibanga rya none", "Current password", "Mot de passe actuel"),
('label_new_password', "Ijambo ry'ibanga rishya", "New password", "Nouveau mot de passe"),
('label_confirm_password', "Emeza ijambo ry'ibanga rishya", "Confirm new password", "Confirmer le nouveau mot de passe"),
('btn_save_name', "Bika izina", "Save Name", "Enregistrer le nom"),
('btn_save_email', "Bika imeli", "Save Email", "Enregistrer l'e-mail"),
('btn_save_shopname', "Bika izina ry'iduka", "Save Shop Name", "Enregistrer le nom de la boutique"),
('btn_save_password', "Hindura ijambo ry'ibanga", "Change Password", "Changer le mot de passe"),
('danger_zone_title', "Ibikorwa biteje akaga", "Danger Zone", "Zone dangereuse"),
('danger_zone_subtitle', "Ibikorwa bikurikira ntibishobora gusubirwaho. Banza utekereze neza.", "Actions below are irreversible. Think carefully before proceeding.", "Les actions ci-dessous sont irréversibles. Réfléchissez bien avant de continuer."),
('delete_account_title', "Siba konti", "Delete Account", "Supprimer le compte"),
('delete_account_desc', "Konti yawe izavanwaho burundu. Inyandiko z'ibikorwa zizabikwa ku mpamvu zo kugenzura gusa.", "Your account will be permanently removed. Transaction records are retained for audit purposes only.", "Votre compte sera supprimé définitivement. Les enregistrements de transactions sont conservés à des fins d'audit uniquement."),
('btn_delete_account', "Siba konti", "Delete Account", "Supprimer le compte"),
('modal_delete_title', "Uzi neza ko ushaka gusiba konti yawe?", "Are you sure you want to delete your account?", "Voulez-vous vraiment supprimer votre compte ?"),
('modal_delete_warning', "Ibi ntibishobora gusubirwaho. Konti yawe izavanwaho burundu.", "This action cannot be undone. Your account will be permanently removed.", "Cette action est irréversible. Votre compte sera supprimé définitivement."),
('modal_type_delete', "Andika <strong>DELETE</strong> kugira ngo wemeze:", "Type <strong>DELETE</strong> to confirm:", "Tapez <strong>DELETE</strong> pour confirmer :"),
('label_your_password_nc', "Ijambo ry'ibanga ryawe", "Your password", "Votre mot de passe"),
('btn_confirm_delete', "Emeza gusiba", "Confirm Deletion", "Confirmer la suppression"),

# ── Chart series (browser) ──────────────────────────────────────────────────
('series_outstanding', "Umwenda usigaye", "Outstanding credit", "Crédit en cours"),
('series_sales', "Inguzanyo zose", "Total credit sales", "Total des ventes à crédit"),
('series_paid', "Ibyishyuwe", "Repaid", "Remboursé"),

# ── CSV export headers ──────────────────────────────────────────────────────
('csv_reference', "Inomero", "Reference", "Référence"),
('csv_date', "Itariki", "Date", "Date"),
('csv_customer', "Umukiriya", "Customer", "Client"),
('csv_type', "Ubwoko", "Type", "Type"),
('csv_amount', "Amafaranga (RWF)", "Amount RWF", "Montant RWF"),
('csv_description', "Ibisobanuro", "Description", "Description"),
('csv_due_date', "Itariki yo kwishyura", "Due date", "Échéance"),

# ── Messages from the server (flash / validation) ───────────────────────────
('msg_register_check', "Reba amakuru watanze: telefoni y'u Rwanda (+2507XXXXXXXX) n'ijambo ry'ibanga rifite nibura inyuguti 10.", "Check your details: Rwanda phone +2507XXXXXXXX, password ≥10 chars.", "Vérifiez vos informations : téléphone rwandais +2507XXXXXXXX, mot de passe d'au moins 10 caractères."),
('msg_account_created', "Konti yafunguwe. Injira.", "Account created. Sign in.", "Compte créé. Connectez-vous."),
('msg_phone_registered', "Iyi numero ya telefoni yamaze kwiyandikisha.", "Phone number already registered.", "Ce numéro de téléphone est déjà inscrit."),
('msg_too_many_attempts', "Wagerageje inshuro nyinshi bikanga. Ongera ugerageze nyuma y'iminota mike.", "Too many failed attempts. Try again in a few minutes.", "Trop de tentatives échouées. Réessayez dans quelques minutes."),
('msg_invalid_login', "Numero ya telefoni cyangwa ijambo ry'ibanga si byo.", "Invalid phone or password.", "Téléphone ou mot de passe invalide."),
('msg_shop_not_found', "Code y'iduka ntiyabonetse.", "Shop code not found.", "Code boutique introuvable."),
('msg_shop_linked', "Iduka ryahujwe neza.", "Shop linked successfully.", "Boutique liée avec succès."),
('msg_cust_not_registered', "Uyu mukiriya ntiyiyandikisha. Musabe kwiyandikisha mbere.", "Customer not registered yet. Ask them to register first.", "Ce client n'est pas encore inscrit. Demandez-lui de s'inscrire d'abord."),
('msg_ask_customer_code', "Saba umukiriya gushyira code y'iduka ryawe muri konti ye.", "Ask the customer to enter your shop code in their dashboard.", "Demandez au client de saisir le code de votre boutique dans son tableau de bord."),
('err_product_name', "Izina ry'igicuruzwa rirakenewe (inyuguti zitarenze 120).", "Product name is required (max 120 characters).", "Le nom du produit est obligatoire (120 caractères maximum)."),
('err_invalid_unit', "Igipimo si cyo.", "Invalid unit.", "Unité invalide."),
('err_invalid_amount', "Shyiramo amafaranga cyangwa umubare ufite agaciro kurenza zeru.", "Enter a valid positive amount.", "Saisissez un montant positif valide."),
('err_invalid_input', "Amakuru watanze si yo cyangwa hari ibibura.", "Invalid or missing input.", "Saisie invalide ou manquante."),
('msg_product_added', "Igicuruzwa «{name}» cyongewe.", "Product “{name}” added.", "Produit « {name} » ajouté."),
('msg_product_updated', "Igicuruzwa «{name}» cyahinduwe.", "Product “{name}” updated.", "Produit « {name} » modifié."),
('err_product_in_use', "Ntushobora gusiba igicuruzwa cyakoreshejwe mu bikorwa. Cyishyire nka «Ntibihari».", "Cannot delete product used in transactions. Mark as unavailable instead.", "Impossible de supprimer un produit utilisé dans des transactions. Marquez-le comme indisponible."),
('msg_product_deleted', "Igicuruzwa cyasibwe.", "Product deleted.", "Produit supprimé."),
('msg_product_marked_available', "Igicuruzwa cyashyizwe ku «Birahari».", "Product marked as available.", "Produit marqué comme disponible."),
('msg_product_marked_unavailable', "Igicuruzwa cyashyizwe ku «Ntibihari».", "Product marked as unavailable.", "Produit marqué comme indisponible."),
('err_add_line_item', "Ongeraho nibura igicuruzwa kimwe.", "Add at least one product line item.", "Ajoutez au moins une ligne de produit."),
('err_too_many_items', "Ibicuruzwa ni byinshi cyane (ntibirenze 50).", "Too many line items (max 50).", "Trop de lignes (50 maximum)."),
('err_invalid_due', "Itariki yo kwishyura si yo.", "Invalid due date.", "Date d'échéance invalide."),
('err_subtotal_small', "Igiteranyo cya «{name}» ni gito cyane.", "Subtotal for “{name}” is too small.", "Le sous-total de « {name} » est trop faible."),
('err_total_range', "Igiteranyo kiri hanze y'ibyemewe.", "Total amount out of valid range.", "Montant total hors limites."),
('err_unknown_product', "Hari igicuruzwa kitazwi mu byatoranyijwe.", "Unknown product in line items.", "Produit inconnu dans les lignes."),
('err_stock', "Ibiri mu bubiko bya «{name}» ntibihagije (biri mu bubiko: {qty} {unit}).", "Not enough stock for “{name}” (available: {qty} {unit}).", "Stock insuffisant pour « {name} » (disponible : {qty} {unit})."),
('msg_sale_saved', "Inguzanyo yabitswe – {ref} – Igiteranyo: {total} RWF", "Credit sale saved – {ref} – Total: {total} RWF", "Vente à crédit enregistrée – {ref} – Total : {total} RWF"),
('err_repay_exceeds', "Ubwishyu ({value} RWF) burenze umwenda usigaye ({bal} RWF).", "Repayment ({value} RWF) exceeds outstanding balance ({bal} RWF).", "Le remboursement ({value} RWF) dépasse le solde impayé ({bal} RWF)."),
('msg_repay_recorded', "Ubwishyu bw'amafaranga mu ntoki bwanditswe: {ref} – {value} RWF", "Cash repayment recorded: {ref} – {value} RWF", "Remboursement en espèces enregistré : {ref} – {value} RWF"),
('err_already_reversed', "Iki gikorwa cyamaze gusubizwa inyuma.", "Already reversed.", "Déjà annulé."),
('err_invalid_reversal', "Gusubiza inyuma ntibyemewe.", "Invalid reversal.", "Annulation invalide."),
('err_reverse_paid', "Ntibishoboka gusubiza inyuma: ibyishyuwe birenze umwenda usigaye.", "Cannot reverse: repayments exceed remaining charge.", "Annulation impossible : les remboursements dépassent le solde restant."),
('msg_reversed', "Igikorwa cyasubijwe inyuma, inyandiko yacyo irabitswe.", "Transaction reversed with audit record.", "Transaction annulée avec trace d'audit."),
('msg_reminder_logged', "Ubwibutso bwanditswe. Nta SMS nyayo yoherejwe.", "Reminder logged. No real SMS sent.", "Rappel enregistré. Aucun vrai SMS envoyé."),
('msg_no_balance', "Uyu mukiriya nta mwenda afite.", "No outstanding balance for this customer.", "Aucun solde impayé pour ce client."),
('err_amount_exceeds', "Amafaranga arenze umwenda usigaye.", "Amount exceeds outstanding balance.", "Le montant dépasse le solde impayé."),
('msg_momo_initiated', "Ubwishyu bwa MoMo bw'IGERAGEZA bwatangiye. Inomero: {ref}", "SIMULATED MoMo payment initiated. Ref: {ref}", "Paiement MoMo SIMULÉ initié. Réf. : {ref}"),
('err_payment_processed', "Ubu bwishyu bwamaze gukorwa.", "Payment already processed.", "Paiement déjà traité."),
('err_balance_changed', "Umwenda wahindutse; ntibishoboka kwemeza.", "Balance changed; cannot confirm.", "Le solde a changé ; confirmation impossible."),
('msg_payment_confirmed', "Ubwishyu bw'IGERAGEZA bwemejwe. Nta mafaranga nyayo yimuwe.", "SIMULATED payment confirmed. No real money moved.", "Paiement SIMULÉ confirmé. Aucun argent réel n'a été déplacé."),
('err_payment_failed', "Ubwishyu bw'igerageza bwanze.", "Simulated payment failed.", "Le paiement simulé a échoué."),
('err_dispute_len', "Andika inyuguti hagati ya 5 na 500.", "Provide 5–500 characters.", "Saisissez entre 5 et 500 caractères."),
('msg_dispute_submitted', "Ikirego cyoherejwe.", "Dispute submitted.", "Litige soumis."),
('msg_dispute_resolved', "Ikirego cyashyizwe ku «Cyakemutse».", "Dispute marked as resolved.", "Litige marqué comme résolu."),
('err_type_reset', "Andika RESET kugira ngo wemeze.", "Type RESET to confirm.", "Tapez RESET pour confirmer."),
('err_wrong_password_reset', "Ijambo ry'ibanga si ryo. Gusiba byahagaritswe.", "Incorrect password. Reset cancelled.", "Mot de passe incorrect. Réinitialisation annulée."),
('err_cannot_reset', "Ntibishoboka gusiba: abakiriya baracyafite umwenda wa {outstanding} RWF. Banza ukemure imyenda cyangwa ukuremo inyandiko.", "Cannot reset: customers still owe {outstanding} RWF. Resolve outstanding debts or export records first.", "Réinitialisation impossible : les clients doivent encore {outstanding} RWF. Réglez les dettes ou exportez les enregistrements d'abord."),
('msg_reset_done', "Inyandiko zose zarasibwe. Inyandiko {count} zabitswe mu rwandiko rwo kugenzura.", "Ledger reset complete. {count} records archived in audit log.", "Registre réinitialisé. {count} enregistrements archivés dans le journal d'audit."),
('err_name_short', "Izina rigomba kugira nibura inyuguti 2.", "Name must be ≥2 characters.", "Le nom doit contenir au moins 2 caractères."),
('msg_name_updated', "Izina ryahinduwe.", "Name updated.", "Nom mis à jour."),
('err_email_invalid', "Imeli si yo.", "Invalid email address.", "Adresse e-mail invalide."),
('msg_email_updated', "Imeli yahinduwe.", "Email updated.", "E-mail mis à jour."),
('err_pw_short', "Ijambo ry'ibanga rishya rigomba kugira nibura inyuguti 10.", "New password must be ≥10 characters.", "Le nouveau mot de passe doit contenir au moins 10 caractères."),
('err_pw_mismatch', "Amajambo y'ibanga ntabwo ahura.", "Passwords do not match.", "Les mots de passe ne correspondent pas."),
('err_pw_current', "Ijambo ry'ibanga rya none si ryo.", "Current password incorrect.", "Mot de passe actuel incorrect."),
('msg_pw_updated', "Ijambo ry'ibanga ryahinduwe.", "Password updated.", "Mot de passe mis à jour."),
('err_shopname_short', "Izina ry'iduka rigomba kugira nibura inyuguti 2.", "Shop name must be ≥2 characters.", "Le nom de la boutique doit contenir au moins 2 caractères."),
('msg_shopname_updated', "Izina ry'iduka ryahinduwe.", "Shop name updated.", "Nom de la boutique mis à jour."),
('err_type_delete', "Andika DELETE kugira ngo wemeze.", "Type DELETE to confirm.", "Tapez DELETE pour confirmer."),
('err_wrong_password_delete', "Ijambo ry'ibanga si ryo. Konti ntiyasibwe.", "Incorrect password. Account not deleted.", "Mot de passe incorrect. Compte non supprimé."),
('msg_account_deleted', "Konti yasibwe.", "Account deleted.", "Compte supprimé."),

# ── Error pages ─────────────────────────────────────────────────────────────
('err_page_title', "Habaye ikibazo", "Something went wrong", "Un problème est survenu"),
('err_400', "Ibyoherejwe si byo cyangwa igihe cyarangiye. Subira inyuma, usubiremo urupapuro, ongere ugerageze.", "The request was invalid or has expired. Go back, reload the page and try again.", "La requête est invalide ou a expiré. Revenez en arrière, rechargez la page et réessayez."),
('err_403', "Ntabwo wemerewe kureba uru rupapuro.", "You are not allowed to view this page.", "Vous n'êtes pas autorisé à voir cette page."),
('err_404', "Urupapuro ntirwabonetse.", "Page not found.", "Page introuvable."),
('err_back_home', "Subira ku rupapuro rwa mbere", "Back to home", "Retour à l'accueil"),
]

TRANSLATIONS = {'rw': {}, 'en': {}, 'fr': {}}
for _key, _rw, _en, _fr in _ROWS:
    assert _key not in TRANSLATIONS['en'], 'duplicate translation key: ' + _key
    TRANSLATIONS['rw'][_key] = _rw
    TRANSLATIONS['en'][_key] = _en
    TRANSLATIONS['fr'][_key] = _fr


class _SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'


def translate(lang, key, **params):
    """Translate `key` into `lang`, falling back to Kinyarwanda, then English."""
    table = TRANSLATIONS.get(lang) or TRANSLATIONS[DEFAULT_LANG]
    text = table.get(key)
    if text is None:
        text = TRANSLATIONS[DEFAULT_LANG].get(key) or TRANSLATIONS['en'].get(key) or key
    if params:
        try:
            text = text.format_map(_SafeDict(params))
        except (ValueError, IndexError):
            pass
    return text
