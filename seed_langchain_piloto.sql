-- =====================================================================
-- Seed: tool_portal -- somente 2 avaliacoes com dados reais
--   [1596077] pilot test        -> python.org        (piloto do instrumento)
--   [2147077] Lang chain portal -> docs.langchain.com (estudo real, 4 participantes)
--
-- Extraido do dump de producao (MySQL 8.0.43, RDS us-east-1).
-- IDs originais preservados. Script IDEMPOTENTE: pode rodar mais de uma vez.
--
-- Uso:  mysql -u USUARIO -p NOME_DO_BANCO < seed_langchain_piloto.sql
-- =====================================================================

SET NAMES utf8mb4;
SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS = 0;
SET @OLD_SQL_MODE = @@SQL_MODE;
SET SQL_MODE = 'NO_AUTO_VALUE_ON_ZERO';

START TRANSACTION;

-- ---------------------------------------------------------------------
-- 0) LIMPEZA das duas avaliacoes (torna o script re-executavel).
--    Nao toca em nenhuma outra avaliacao do seu banco local.
-- ---------------------------------------------------------------------
SET @ev1 = 1596077;
SET @ev2 = 2147077;

DELETE a FROM `answer` a
  JOIN `collected_data` cd ON cd.collected_data_id = a.collected_data_id
  WHERE cd.evaluation_id IN (@ev1, @ev2);
DELETE dq FROM `developer_questionnaire` dq
  JOIN `collected_data` cd ON cd.collected_data_id = dq.collected_data_id
  WHERE cd.evaluation_id IN (@ev1, @ev2);
DELETE n FROM `navigation` n
  JOIN `collected_data` cd ON cd.collected_data_id = n.collected_data_id
  WHERE cd.evaluation_id IN (@ev1, @ev2);
DELETE pt FROM `performed_task` pt
  JOIN `collected_data` cd ON cd.collected_data_id = pt.collected_data_id
  WHERE cd.evaluation_id IN (@ev1, @ev2);
DELETE hp FROM `heatmap_points` hp
  JOIN `collected_data` cd ON cd.collected_data_id = hp.collected_data_id
  WHERE cd.evaluation_id IN (@ev1, @ev2);
DELETE FROM `collected_data`          WHERE evaluation_id IN (@ev1, @ev2);
DELETE FROM `evaluation_ksc_weight`   WHERE evaluation_id IN (@ev1, @ev2);
DELETE FROM `evaluation_SECO_process` WHERE evaluation_id IN (@ev1, @ev2);
DELETE FROM `evaluation`              WHERE evaluation_id IN (@ev1, @ev2);


-- =====================================================================
-- 1) CATALOGO (dados de referencia do instrumento).
--    INSERT IGNORE: se o seu banco local ja tiver esse seed, nada muda.
-- =====================================================================

INSERT IGNORE INTO `seco_dimension` (`seco_dimension_id`,`name`) VALUES
  (1,'Technical'),
  (2,'Business'),
  (3,'Social');
-- 3 linha(s) em `seco_dimension`

INSERT IGNORE INTO `seco_process` (`seco_process_id`,`description`) VALUES
  (1,'Access to documentation, source code, and tools.'),
  (2,'Access to information about the code in repositories.'),
  (3,'Communication channels between actors and keystone.'),
  (4,'Processes related to SECO governance.'),
  (5,'Access to information about requirements flow.'),
  (6,'Processes related to data collection, processing, and sharing.'),
  (7,'Access to information about SECO architecture.');
-- 7 linha(s) em `seco_process`

INSERT IGNORE INTO `conditioning_factor_transp` (`conditioning_factor_transp_id`,`description`) VALUES
  (1,'The existence of communication channels between actors and keystone.'),
  (2,'Information about platform made available in an accessible way.'),
  (3,'The actors\' understanding of SECO information.'),
  (4,'The quality of platform information provided by a keystone.'),
  (5,'The usability of interfaces with platform documentation.'),
  (6,'The auditability of platform processes and information.'),
  (7,'Visualization of the evolution of projects in SECO.'),
  (8,'Reliability of information provided by a keystone.');
-- 8 linha(s) em `conditioning_factor_transp`

INSERT IGNORE INTO `dx_factor` (`dx_factor_id`,`description`) VALUES
  (1,'Desired technical resources for development.'),
  (2,'Easy to configure platform.'),
  (3,'Financial costs for using the platform.'),
  (4,'Diversity of services provided by the platform.'),
  (5,'Platform transparency.'),
  (6,'Documentation quality.'),
  (7,'Existence of communication channels.'),
  (8,'Platform openness level.'),
  (9,'More clients/users for applications.'),
  (10,'Application distribution methods.'),
  (11,'Application interface and appearance standards.'),
  (12,'Requirements for developing applications over a platform.'),
  (13,'Ease of learning about technology.'),
  (14,'Low barriers to entry into the applications market.'),
  (15,'Obtaining community recognition.'),
  (16,'Commitment to the community.'),
  (17,'A good relationship with the community.'),
  (18,'Knowledge exchange between community developers.'),
  (19,'A good developer relations program.'),
  (20,'Community size and scalability.'),
  (21,'Emergence of new market and job opportunities.'),
  (22,'More financial gains.'),
  (23,'Fun while developing.'),
  (24,'Improvement of developer skills and intellect.'),
  (25,'Autonomy and self-control of workflow.'),
  (26,'Qualities and characteristics of the software ecosystem platform.'),
  (27,'Engagement and rewards for work.');
-- 27 linha(s) em `dx_factor`

INSERT IGNORE INTO `guideline` (`guidelineID`,`title`,`description`,`notes`) VALUES
  (1,'Provide Access to Documentation, Source Code, and Development Tools','Software ecosystems portals must centralize and keep up to date all developer resources (e.g., documentation, source code, and tools) through a unified and consistent access point. These materials should be easy to locate, well-structured, and regularly maintained to avoid fragmentation or outdated content. In hybrid or proprietary software ecosystems, some resources cannot be public due to intellectual property or security restrictions. Yet, transparency remains essential: portals should indicate what exists, how it can be accessed under authorization, and how it is maintained. Clear organization, explicit access policies, and reliable search features sustain trust and reduce onboarding time.','Transparent and well-organized access to documentation, code, and tools is essential for an effective and equitable developer experience. Portals should provide centralized and discoverable resources, ensuring accurate, versioned, and multilingual information. Even in PSECO, transparency can be maintained through traceable and authorized access mechanisms. Ecosystems strengthen trust, lower barriers to entry, and support global collaboration by promoting clarity, inclusiveness, and proportional openness.'),
  (2,'Ensure Access to Repository History and Code Evolution','Software ecosystem portals must provide developers with clear and traceable information about repository activity and evolution. Transparency goes beyond access to source code and requires visibility into who contributed what, when, and why, supported by metadata, logs, and contribution records. Portals should also expose indicators of repository vitality, including activity and popularity metrics such as update frequency, contributor engagement, number of stars or forks, and release history. In proprietary or hybrid software ecosystems, this visibility can be maintained through summaries, dashboards, or changelogs that communicate progress without exposing sensitive code or internal components.','Transparent access to repository history and evolution strengthens trust, accountability, and collaborative learning within software ecosystems. Beyond exposing code, effective transparency involves providing interpretable metadata, contribution records, and activity indicators that reveal how the platform evolves over time. Indicators of vitality and popularity help developers assess the ecosystem’s health and openness.'),
  (3,'Establish Communication Channels Between Developers and the Keystone','Software ecosystem portals must ensure transparent, reliable, and responsive communication channels between developers and the keystone. These channels should be official and visible through the portal, enabling traceable and accountable interactions that allow developers to follow discussions and outcomes. Portals should offer diverse and moderated spaces for questions, feedback, and announcements, ensuring responsiveness and clarity about who communicates on behalf of the keystone. In hybrid or proprietary software ecosystems, communication must also prevent unintended disclosure of corporate or strategic information by adopting secure and auditable channels that preserve trust and confidentiality.','Transparent communication strengthens trust, accountability, and collaboration between the keystone and external developers. Official and moderated channels ensure that interactions are visible, traceable, and reliable, allowing developers to follow discussions and outcomes with confidence. Maintaining multiple but consistently managed channels supports openness and adaptability while preventing information loss or disclosure of sensitive content.'),
  (4,'Publish Participation Rules, Contribution Guidelines, and Compliance Requirements','Software ecosystem portals must publish clear and accessible participation rules, contribution guidelines, and developer involvement compliance requirements. These policies should define expectations, acceptance criteria, and technical, legal, and security contribution requirements. Transparent publication of such rules strengthens trust, accountability, and predictability in developer participation. In hybrid or proprietary software ecosystems, only non-confidential compliance information should be disclosed, while ensuring that participation criteria remain visible and understandable to external contributors.','Transparent publication of participation and compliance rules builds confidence and fairness in software ecosystems. Developers must be able to locate, understand, and anticipate the requirements that govern their participation. Maintaining clear and up-to-date guidelines reduces uncertainty, strengthens trust, and ensures accountability in the relationship between the keystone and the developer community.'),
  (5,'Document the Flow of Requirements, Feature Requests, and Roadmap Decisions','Developers need visibility into how platform requirements, feature requests, and roadmap decisions are handled. When submission and decision processes are unclear, developers cannot align their work with the platform’s evolution. The portal should describe how requests are submitted, reviewed, prioritized, and transformed into roadmap updates, ensuring coordination and accountability. Transparency must balance openness with security and privacy concerns, avoiding exposure of confidential information. In hybrid or proprietary software ecosystems, summarized or aggregated decision records may replace full disclosure, as long as external developers can still understand the platform’s rationale and direction.','Transparency in how requirements and roadmap decisions are managed strengthens collaboration, trust, and shared understanding among developers. Making submissions, reviews, and decisions visible allows contributors to see how their input influences the platform’s direction. Clear documentation of changes and rationales ensures accountability, autonomy, and continuity in the ecosystem’s evolution. In hybrid or proprietary contexts, even partial visibility through summaries or progress indicators can meaningfully enhance understanding and predictability for external developers.'),
  (6,'Clarify Data Collection, Processing, and Sharing Practices','Software ecosystem portals must clearly describe how data from developers and their applications is collected, processed, and shared. Transparency in data practices builds trust and ensures informed participation. The portal should identify what information is gathered through analytics, authentication, or submission tools, and explain its purpose using clear language and visual means. Data visibility must balance openness with privacy and security, employing anonymization, aggregation, and explicit consent where needed. In hybrid or proprietary software ecosystems, summarized dashboards or simplified explanations may replace full disclosure, provided the rationale and impact of data use remain understandable to developers.','Transparency in data collection and sharing reinforces ethical responsibility, legal compliance, and trust among ecosystem actors. Clear, visual, and verifiable explanations help developers understand how their information is used and empower them to make informed decisions. In hybrid or proprietary contexts, summarized or anonymized disclosures can still sustain fairness and predictability in platform–developer relations.'),
  (7,'Present the Architecture and Structural Composition of the Software Ecosystem','Understanding the architecture of a software ecosystem is essential for developers to integrate, contribute, and make technical decisions. The portal should present clear, visual, and up-to-date representations of the ecosystem’s structure, showing components, modules, services, and their relationships. Transparency in architectural information improves alignment and confidence, but must respect confidentiality and intellectual property boundaries. In hybrid or proprietary software ecosystems, functional overviews or summarized diagrams may replace detailed views to balance openness and protection. This proportional approach enables understanding without compromising strategic or sensitive information.','Transparent architectural information enables developers to make informed integration and design choices while building trust in the platform’s maturity. In open ecosystems, this transparency fosters collective understanding and reuse. In hybrid or proprietary contexts, functional overviews or abstracted diagrams can maintain this trust without compromising confidentiality or intellectual property. Keeping diagrams current and accessible signals organizational reliability and technical coherence.');
-- 7 linha(s) em `guideline`

INSERT IGNORE INTO `key_success_criterion` (`key_success_criterion_id`,`title`,`description`,`guideline_id`) VALUES
  (1,'Centralized and Navigable Documentation','Documentation must be centralized and accessible from the portal, with stable links, minimal barriers, and clear navigation. It should include search tools and cross-references to ensure quick access to accurate information. In proprietary software ecosystems (PSECO), summaries or indexed views should indicate what exists and how it can be requested.',1),
  (2,'Public Access to Source Code Repositories','Repositories must be clearly identified and accessible through the portal, including information about location, structure, and version history. Visibility should allow developers to understand the codebase and the contribution workflow. In PSECO, public summaries or changelogs should indicate repository existence and evolution without exposing sensitive code.',1),
  (3,'Availability and Versioning of Development Tools','Development tools such as SDKs, APIs, and CLIs must be accessible through the portal with clear version information, changelogs, and compatibility details. Updates should be traceable so developers can maintain stable environments and avoid integration issues.',1),
  (4,'Equitable and Multilingual Documentation','Documentation must be available in multiple languages, accurate, and kept up to date to ensure equal access to technical information. Equitable documentation practices promote shared understanding, collaboration, and trust among developers in different contexts.',1),
  (5,'Availability of Repository Location and Visibility Information','Repositories must be clearly listed and accessible from the portal, with visible information about their purpose, location, and maintenance status. The portal should ensure consistent visibility of all repositories, avoiding broken links or hidden components. In hybrid or proprietary software ecosystems, summaries or indexed views should indicate restricted repositories and access conditions.',2),
  (6,'Presence of Repository Metadata and Contribution Documentation','Each repository must include clear metadata describing its purpose, maintainers, update history, and contribution process. Documentation should specify how to contribute, review changes, and track decision rationales. In hybrid or proprietary software ecosystems, anonymized or summarized contribution logs should maintain traceability without exposing sensitive details.',2),
  (7,'Traceability of Code Contributions and Changes','Repositories must provide traceable records of code contributions and modifications, including authorship, timestamps, and references to related issues or reviews. Traceability should enable developers to understand how and why changes occurred. In hybrid or proprietary sofwtare ecosystems, summarized changelogs or dashboards can ensure visibility without disclosing restricted content.',2),
  (8,'Availability of Official Contact Channels','Portals must provide official, visible, and accessible communication channels between the keystone and external developers, clearly listing options such as support emails, helpdesk forms, chat groups, or issue trackers. These channels should be moderated, reliable, and consistently maintained, allowing multiple forms of communication to coexist as long as they remain easy to locate and officially recognized through the portal.',3),
  (9,'Responsiveness and Traceability of Interactions','Communication channels must ensure responsive and traceable interactions between external developers and the keystone. Developers should be able to track discussions, decisions, and response times, knowing who provided the answer and when. In hybrid or proprietary software ecosystems, summarized or anonymized records may preserve accountability while protecting sensitive or strategic information.',3),
  (10,'Clarity of Roles and Communication Responsibilities','Communication channels must clearly identify who communicates on behalf of the keystone and their specific roles in the ecosystem. Developers should be able to distinguish official statements, announcements, or decisions from personal opinions. The portal must ensure visible ownership of posts or messages, maintaining institutional accountability and preventing misinformation.',3),
  (12,'Publication and Accessibility of Participation Rules','Portals must clearly publish and maintain official participation, contribution, and compliance rules, including technical, legal, and security requirements. These rules should be visible, up to date, and easy to understand, ensuring that developers know how to join, contribute, and comply with ecosystem standards.',4),
  (13,'Clarity of Acceptance and Compliance Criteria','Portals must clearly describe the acceptance and compliance criteria applied to contributions, explaining how they are reviewed, approved, or rejected, and under which technical, legal, or security conditions. These criteria should be public, consistent, and easy to interpret, ensuring fairness, predictability, and trust in the contribution process.',4),
  (14,'Visibility of Governance and Policy Updates','Portals must make governance and policy updates visible and traceable, clearly indicating what has changed, when, and why. Developers should be promptly informed of modifications to participation, compliance, or contribution requirements through public changelogs or update dashboards, ensuring predictability and accountability in the evolution of ecosystem policies.',4),
  (15,'Clear Channels for Submitting Requirements or Feedback','Portals must clearly indicate where and how developers can submit feature requests, bug reports, or improvement proposals. The submission process should distinguish between different types of requirements (e.g., related to the portal, the platform, or hosted products), ensuring clarity and proper routing of feedback. It must also be intuitive and consistent across tools, allowing contributors to participate without ambiguity or excessive effort.',5),
  (16,'Transparent Review and Prioritization Process','Portals must describe how submitted items are reviewed and prioritized, specifying the criteria, responsible actors, and expected response times. Both strategic and emerging requirements should be considered, with transparent criteria for handling immediate community demands versus long-term roadmap goals. The decision workflow should be traceable and applied consistently, showing how requests move from evaluation to implementation or rejection.',5),
  (17,'Public Access to Roadmaps and Change Plans','Portals must provide public and continuously updated roadmaps or changelogs that show planned features, improvements, and deprecated elements. Each update should be traceable to prior discussions or documented decisions, illustrating how feedback and requirements shape the platform’s evolution. In sensitive contexts, roadmaps may highlight goals and progress without revealing confidential or security-critical information.',5),
  (18,'Clarity About Data Collected and Its Purpose','Portals must clearly state what data is collected from developers and their applications, through analytics, authentication, or submission tools, and explain why. Information must be communicated in simple language and, when possible, supported by visual summaries to make collection practices understandable and verifiable.',6),
  (19,'Transparent Processing and Consent Mechanisms','Portals must describe how collected data are processed, stored, and secured, clarifying who has access and under what legal or operational basis. Explicit consent, anonymization, and aggregation practices should be applied to preserve developer privacy while keeping information auditable.',6),
  (20,'Visibility into Data Sharing and Third-Party Access','Portals must make visible how and when data are shared with third parties, APIs, or analytics providers, and for what purpose. Disclosures should use clear text or visual indicators rather than legal jargon, helping developers understand risks and accountability chains.',6),
  (21,'Visual or Descriptive Representation of Ecosystem Architecture','Portals must provide visual or textual representations that describe the ecosystem’s main components, modules, and interaction flows. These representations should offer a functional overview that helps developers understand integration points and dependencies without revealing proprietary or sensitive design details.',7),
  (22,'Clarity About Component Responsibilities and Relationships','Portals must describe what each major component, service, or API is responsible for and how they interact with the core platform and external systems. Explanations should be concise, avoiding low-level technical exposure that could compromise intellectual property.',7),
  (23,'Updated and Versioned Architectural Information','Architectural documentation must be regularly reviewed and updated to reflect the current ecosystem structure. Versioning or change logs should indicate what has evolved, helping developers track the platform’s growth and evolution over time.',7);
-- 22 linha(s) em `key_success_criterion`

INSERT IGNORE INTO `question` (`question_id`,`question`,`key_success_criterion_id`) VALUES
  (1,'How much did you perceive that the portal offered centralized and easily navigable documentation to support your work?',1),
  (2,'How much did you perceive that the portal made repositories clearly visible and accessible from a unified entry point?',2),
  (3,'How much did you perceive that the portal provided access to development tools (e.g., SDK, API, CLI) with clear version information and update history?',3),
  (4,'How much did you perceive that the portal offered documentation in multiple languages with consistent and up-to-date content?',4),
  (5,'How much did you perceive that the portal made repositories easily identifiable, with visible information about their purpose, location, and maintenance status?',5),
  (6,'How much did you perceive that the portal provided repository metadata and contribution documentation describing maintainers, update history, and participation workflow?',6),
  (7,'How much did you perceive that the portal enabled traceability of code contributions and modifications through visible records of commits, issues, or change logs?',7),
  (8,'How much did you perceive that the portal provided visible and official communication channels to contact the keystone or support team?',8),
  (9,'How much did you perceive that the portal ensured responsiveness and traceability of interactions, allowing visibility into discussions or outcomes?',9),
  (10,'How much did you perceive that the portal clearly identified who communicates on behalf of the keystone, distinguishing official responses from personal opinions?',10),
  (12,'How much did you perceive that the portal published and made accessible the official participation, contribution, and compliance rules of the ecosystem?',12),
  (13,'How much did you perceive that the portal clearly described the acceptance and compliance criteria used to review and approve contributions?',13),
  (14,'How much did you perceive that the portal made governance and policy updates visible and traceable, showing what has changed, when, and why?',14),
  (15,'How much did you perceive that the portal made clear where and how developers can submit requirements, feature requests, or improvement proposals?',15),
  (16,'How much did you perceive that the portal provided visibility into how submitted items are reviewed and prioritized, including criteria, responsible actors, and response timelines?',16),
  (17,'How much did you perceive that the portal offered public access to roadmaps or changelogs showing planned features, improvements, and rationale for decisions?',17),
  (18,'How much did you perceive that the portal clearly presented what data is collected from developers and their applications, along with its purpose?',18),
  (19,'How much did you perceive that the portal described how collected data is processed, stored, and secured, clarifying consent and access mechanisms?',19),
  (20,'How much did you perceive that the portal made visible how and when data is shared with third parties or external services, including the purpose of sharing?',20),
  (21,'How much did you perceive that the portal provided visual or descriptive representations showing the ecosystem’s main components, modules, and interaction flows?',21),
  (22,'How much did you perceive that the portal clearly described each component’s responsibilities and relationships with other parts of the system?',22),
  (23,'How much did you perceive that the portal kept architectural information updated and versioned, showing when and how structural changes occurred?',23);
-- 22 linha(s) em `question`

INSERT IGNORE INTO `example` (`example_id`,`description`,`key_success_criterion_id`) VALUES
  (1,'Map all existing documentation and restructure it into a single, coherent information architecture. Implement or enhance a search function and clear hierarchy for topics. Identify duplicated or outdated content for removal. In SECOP, define visibility levels and provide standardized request channels for restricted materials. For instance, GitHub Docs and Android Developers centralize all documentation under a unified entry point with integrated search and cross-links, offering a clear reference for structure and usability.',1),
  (2,'List all repositories in a dedicated section of the portal, with direct links, contribution guidelines, and version details. Include visible metadata such as last update, maintainers, and repository purpose. In PSECO, publish summarized logs or release reports that communicate evolution transparently. For instance, the Eclipse Foundation presents repository directories with metadata, recent activity, and contribution paths, ensuring clarity and traceability.',2),
  (3,'Provide a dedicated section for SDK, API, and CLI downloads, including version history, compatibility matrix, and support lifecycle. Highlight deprecated tools and link to their replacements. For instance, the Android Developers portal maintains versioned tool pages with changelogs and support policies that ensure predictable updates and long-term reliability.',3),
  (4,'Develop translation and review workflows that guarantee parity between all language versions whenever updates occur. Clearly show last update dates and revision notes in each version. For instance, Mozilla Developer Network (MDN) maintains multilingual parity through community translation pipelines and automated synchronization.',4),
  (5,'Create a dedicated repository directory within the portal, displaying each repository’s name, purpose, link, and last update. Use filters and metadata to distinguish public, partner, or internal repositories. For instance, Eclipse Foundation and Apache Software Foundation portals organize repositories in structured indexes with update indicators and access labels, ensuring transparency even in complex ecosystems.',5),
  (6,'Ensure that every repository includes a metadata file and a contribution guide describing roles, workflow, and update frequency. Add maintainers’ contact information, last revision dates, and change documentation. For instance, GitLab and OpenStack portals provide detailed metadata and contribution guidelines that document ownership, participation, and project evolution transparently.',6),
  (7,'Integrate automated tools that track commits, pull requests, and issue links, displaying this data in a clear timeline or dashboard. Ensure that each change references its rationale and responsible contributor. For instance, GitHub Insights and Eclipse Project Dash visualize commits, contributors, and code reviews to communicate project evolution transparently.',7),
  (8,'Identify all official communication channels and ensure their visibility through the portal, regardless of where they are hosted. Maintain coherence and consistent updates across multiple channels, marking each as official and moderated. Periodically review inactive or redundant spaces to preserve clarity and trust in the ecosystem’s communication network. For instance, the Eclipse Foundation Portal centralizes links to its forums, Slack workspaces, and GitLab issue trackers, each labeled as official and actively moderated to ensure consistent visibility across tools.',8),
  (9,'Adopt mechanisms to monitor and display response times, responsible actors, and discussion outcomes within official channels. Provide summaries or logs of relevant interactions, ensuring follow-up and closure visibility without exposing confidential content. For instance, the Mozilla Developer Portal displays labeled discussions and issue threads showing responsible teams, timestamps, and resolution status, maintaining responsiveness and accountability.',9),
  (10,'Display the names or roles of official representatives in each communication channel, and label verified or keystone-issued messages. Establish moderation policies to prevent impersonation or confusion about authority. For instance, the Kubernetes Portal identifies maintainers and SIG (Special Interest Group) leads as verified responders in public discussions, ensuring clarity about roles and communication authority.',10),
  (12,'Create a dedicated section within the portal for participation and compliance policies, organizing them by contribution type and keeping version history visible. Periodically review the clarity and accessibility of these documents with community feedback. For instance, the Android Developers Portal provides a “Policy Center” with explicit participation rules, contribution steps, and licensing terms, ensuring consistent communication of expectations and compliance.',12),
  (13,'Publish detailed contribution workflows and acceptance criteria within the portal, linking each stage to the responsible reviewers or governance roles. Include examples of accepted and rejected submissions to illustrate compliance expectations. For instance, the Eclipse Foundation Portal documents its contribution and IP review process, specifying technical and legal checks before approval and showing examples of rejected contributions for transparency.',13),
  (14,'Create a dedicated section or changelog within the portal that lists and timestamps all modifications to participation and compliance rules. Provide concise summaries explaining each change and maintain an accessible archive of previous versions for reference. For instance, the Apple Developer Portal publishes policy changelogs that specify dates, affected sections, and rationale for updates, allowing developers to track governance evolution transparently.',14),
  (15,'Create visible and standardized submission entry points (buttons, forms, or issue trackers) linked from the portal’s main navigation. Integrate these channels with feedback tools or public spaces where developers can discuss or refine proposals. For instance, GitLab and GitHub provide accessible issue tracking systems that allow developers to create, label, and discuss feature requests and bug reports collaboratively.',15),
  (16,'Publish a structured review workflow that defines evaluation steps, responsible maintainers, prioritization rules, and response timelines. Provide access to decision logs or summaries that explain how and why each request was addressed. For instance, the Django project maintains detailed triage and prioritization policies that clarify reviewer roles, criteria, and decision outcomes for all community proposals.',16),
  (17,'Maintain a roadmap or update dashboard linking planned features to their corresponding discussions or requests. Complement this with release notes, summary reports, or governance updates that explain key changes and their motivations. For instance, the Node.js ecosystem maintains a public roadmap and change dashboard linking each planned feature to its related issues and community discussions.',17),
  (18,'Publish a dedicated “Data Use Overview” page with visual summaries of collected data categories, purposes, and retention periods. Include real examples of consent prompts or tracking preferences available to developers. For instance, the Microsoft Partner Center presents data collection purposes through a structured dashboard and contextual explanations during tool usage.',18),
  (19,'Document processing pipelines and access levels, and implement consent dashboards where developers can manage their data-sharing preferences. Provide audit trails or public compliance statements verifying data-handling integrity. For instance, the Eclipse Foundation publishes detailed privacy and consent management procedures, specifying roles, retention periods, and anonymization techniques.',19),
  (20,'Provide a table or interactive view listing partner organizations, shared data types, and access frequency. In hybrid or proprietary ecosystems, use aggregated summaries that indicate data categories and sharing rationale without revealing sensitive details. For instance, the Google Cloud Console offers a “Data Access Transparency” dashboard showing which partners accessed what data and for what purpose.',20),
  (21,'Create a dedicated “Architecture Overview” section with layered diagrams, conceptual models, or structured descriptions showing the ecosystem’s organization. Ensure that diagrams highlight relationships between core services, APIs, and external modules. For instance, the Kubernetes Documentation Portal provides an interactive layered diagram of control plane and node components, explaining each layer’s purpose without exposing internal configurations.',21),
  (22,'Use tables or labeled diagrams summarizing the function, interfaces, and dependencies of each component. Provide links to API references or documentation sections explaining how developers can interact safely with each part of the system. For instance, the Eclipse Platform Architecture page lists subsystems and clarifies their interactions with the IDE core, using role-based and dependency diagrams.',22),
  (23,'Include version tags, update timestamps, and historical diagrams that illustrate structural changes. Integrate architecture documentation with repositories or dashboards that update automatically when core components change. For instance, the GitLab Docs site maintains versioned architecture diagrams that link to historical releases, showing how core services and integrations evolved across versions.',23);
-- 22 linha(s) em `example`

INSERT IGNORE INTO `task` (`task_id`,`title`,`description`,`summary`) VALUES
  (1,'Exploring Resources to Start Development','Imagine that you have just joined a project within this software ecosystem and need to start a new integration with the platform. Your goal is to quickly find the materials you need, such as technical documentation, code repositories, and development tools (e.g., SDK, API, CLI), so that you can prepare your environment and understand where to start. Explore the portal freely, as you would in a real situation, until you feel you have found the information you need to begin your development work.','Represents developers’ first interaction with the ecosystem portal. Clear and accessible documentation here directly impacts onboarding speed and confidence.'),
  (2,'Exploring Repository History and Code Evolution','Imagine that you are contributing to a software ecosystem project and want to understand how the platform’s codebase has evolved over time. Your goal is to find clear and traceable information about repository activity, such as contribution history, metadata, or change logs (e.g., commits, pull requests, release notes), so that you can understand who contributed what, when, and why. Explore the portal freely, as you would in a real situation, until you feel you have found enough information to comprehend the repository’s evolution and vitality.','Represents how developers explore repositories to understand the platform’s evolution. Traceable and well-documented code changes increase trust and ease of contribution.'),
  (3,'Exploring Communication Channels with the Keystone','Imagine that you are developing or maintaining a project within this software ecosystem and need to contact the keystone (organization that manages the platform) team to ask a question, report an issue, or provide feedback. Your goal is to identify and access the official communication channels available through the portal, such as support emails, discussion forums, or chat platforms (e.g., Slack, Discord, or GitHub Discussions), to understand how communication with the keystone occurs and how responses are managed. Explore the portal freely, as you would in a real situation, until you feel you have found the channels and information necessary to contact or follow discussions with the keystone team.','Represents how developers connect with ecosystem actors to clarify doubts or propose changes. Transparent and responsive communication fosters collaboration and knowledge flow.'),
  (4,'Exploring Participation Rules and Contribution Guidelines','Imagine that you are planning to contribute to the platform and need to understand the rules and requirements that guide participation in this software ecosystem. Your goal is to locate and review information about participation policies, such as contribution guidelines, compliance requirements, and governance rules (e.g., legal terms, security standards, or acceptance criteria), so that you can understand what is expected from contributors. Explore the portal freely, as you would in a real situation, until you feel you have found the information needed to understand how participation and compliance are managed.','Represents how developers learn the rules, processes, and compliance requirements for contributing. Clear guidance reduces cognitive effort and prevents frustration or missteps.'),
  (5,'Exploring the Flow of Requirements and Roadmap Decisions','Imagine that you are a developer who wants to understand how new ideas, feature requests, or improvement proposals are handled in this software ecosystem. Your goal is to find information about how requirements are submitted, reviewed, and prioritized, such as channels for feedback, evaluation criteria, and roadmap updates (e.g., feature requests, bug reports, or policy changes), so that you can understand how decisions evolve within the platform. Explore the portal freely, as you would in a real situation, until you feel you have found enough information to understand how requirements and roadmap decisions are managed.','Represents how developers track how new ideas, feature requests, and improvements are evaluated and prioritized. Visible decision flows increase predictability and engagement.'),
  (6,'Exploring Data Collection and Sharing Practices','Imagine that you are a developer using this software ecosystem and want to understand how your data, or the data from your applications, is collected, processed, and shared. Your goal is to find information about data management practices, such as what is collected, how it is used, and who has access (e.g., analytics data, authentication details, or usage statistics), so that you can understand how the platform handles privacy, security, and transparency. Explore the portal freely, as you would in a real situation, until you feel you have found enough information to understand how data collection and sharing are managed.','Represents how developers seek clarity about what data is collected, processed, and shared within the platform. Transparent practices build reliability and ethical trust.'),
  (7,'Exploring the Architecture and Structure of the Ecosystem','Imagine that you are a developer who needs to understand how the platform is organized to integrate or build new components within this software ecosystem. Your goal is to find clear and up-to-date information about the ecosystem’s architecture, such as diagrams, component descriptions, and interaction flows (e.g., modules, services, API, or external integrations), so that you can understand how the platform is structured and how its parts connect. Explore the portal freely, as you would in a real situation, until you feel you have found enough information to understand the ecosystem’s architecture and organization.','Represents how developers understand the overall architecture of the ecosystem. Clear technical maps and dependencies reduce mental load and improve comprehension of how components interact.');
-- 7 linha(s) em `task`

INSERT IGNORE INTO `task_seco_type` (`task_id`,`seco_type`) VALUES
  (1,'OPEN_SOURCE'),
  (1,'HYBRID'),
  (1,'PROPRIETARY'),
  (2,'OPEN_SOURCE'),
  (2,'HYBRID'),
  (2,'PROPRIETARY'),
  (3,'OPEN_SOURCE'),
  (3,'HYBRID'),
  (3,'PROPRIETARY'),
  (4,'OPEN_SOURCE'),
  (4,'HYBRID'),
  (4,'PROPRIETARY'),
  (5,'OPEN_SOURCE'),
  (5,'HYBRID'),
  (5,'PROPRIETARY'),
  (6,'OPEN_SOURCE'),
  (6,'HYBRID'),
  (6,'PROPRIETARY'),
  (7,'OPEN_SOURCE'),
  (7,'HYBRID'),
  (7,'PROPRIETARY');
-- 21 linha(s) em `task_seco_type`

INSERT IGNORE INTO `guideline_seco_dimension` (`guideline_id`,`seco_dimension_id`) VALUES
  (1,1),
  (1,2),
  (1,1),
  (1,2),
  (2,3),
  (2,1),
  (2,3),
  (2,1),
  (3,2),
  (3,3),
  (3,2),
  (3,3),
  (4,2),
  (4,3),
  (4,1),
  (4,2),
  (4,3),
  (4,1),
  (5,2),
  (5,3),
  (5,2),
  (5,3),
  (6,1),
  (6,2),
  (6,3),
  (6,1),
  (6,2),
  (6,3),
  (7,1),
  (7,2),
  (7,1),
  (7,2);
-- 32 linha(s) em `guideline_seco_dimension`

INSERT IGNORE INTO `guideline_seco_process` (`guideline_id`,`seco_process_id`) VALUES
  (1,1),
  (1,1),
  (2,2),
  (2,2),
  (3,3),
  (3,3),
  (4,4),
  (4,4),
  (5,5),
  (5,5),
  (6,6),
  (6,6),
  (7,7),
  (7,7);
-- 14 linha(s) em `guideline_seco_process`

INSERT IGNORE INTO `guideline_conditioning_factor` (`guideline_id`,`conditioning_factor_transp_id`) VALUES
  (1,4),
  (1,2),
  (1,5),
  (1,4),
  (1,2),
  (1,5),
  (2,3),
  (2,7),
  (2,6),
  (2,3),
  (2,7),
  (2,6),
  (3,8),
  (3,1),
  (3,3),
  (3,8),
  (3,1),
  (3,3),
  (4,2),
  (4,4),
  (4,8),
  (4,3),
  (4,2),
  (4,4),
  (4,8),
  (4,3),
  (5,3),
  (5,2),
  (5,6),
  (5,7),
  (5,3),
  (5,2),
  (5,6),
  (5,7),
  (6,8),
  (6,2),
  (6,4),
  (6,6),
  (6,8),
  (6,2);
INSERT IGNORE INTO `guideline_conditioning_factor` (`guideline_id`,`conditioning_factor_transp_id`) VALUES
  (6,4),
  (6,6),
  (7,2),
  (7,4),
  (7,8),
  (7,7),
  (7,3),
  (7,2),
  (7,4),
  (7,8),
  (7,7),
  (7,3);
-- 52 linha(s) em `guideline_conditioning_factor`

INSERT IGNORE INTO `guideline_dx_factor` (`guideline_id`,`dx_factor_id`) VALUES
  (1,1),
  (1,2),
  (1,14),
  (1,6),
  (1,13),
  (1,5),
  (1,26),
  (1,1),
  (1,2),
  (1,14),
  (1,6),
  (1,13),
  (1,5),
  (1,26),
  (2,6),
  (2,5),
  (2,13),
  (2,18),
  (2,6),
  (2,5),
  (2,13),
  (2,18),
  (3,18),
  (3,5),
  (3,7),
  (3,17),
  (3,26),
  (3,18),
  (3,5),
  (3,7),
  (3,17),
  (3,26),
  (4,5),
  (4,10),
  (4,12),
  (4,26),
  (4,14),
  (4,5),
  (4,10),
  (4,12);
INSERT IGNORE INTO `guideline_dx_factor` (`guideline_id`,`dx_factor_id`) VALUES
  (4,26),
  (4,14),
  (5,26),
  (5,12),
  (5,5),
  (5,18),
  (5,25),
  (5,26),
  (5,12),
  (5,5),
  (5,18),
  (5,25),
  (6,5),
  (6,24),
  (6,5),
  (6,26),
  (6,25),
  (6,5),
  (6,24),
  (6,5),
  (6,26),
  (6,25),
  (7,18),
  (7,5),
  (7,26),
  (7,13),
  (7,6),
  (7,5),
  (7,18),
  (7,18),
  (7,5),
  (7,26),
  (7,13),
  (7,6),
  (7,5),
  (7,18);
-- 76 linha(s) em `guideline_dx_factor`

INSERT IGNORE INTO `process_task` (`seco_process_id`,`task_id`) VALUES
  (1,1),
  (1,1),
  (2,2),
  (2,2),
  (3,3),
  (3,3),
  (4,4),
  (4,4),
  (5,5),
  (5,5),
  (6,6),
  (6,6),
  (7,7),
  (7,7);
-- 14 linha(s) em `process_task`


-- =====================================================================
-- 2) USUARIO dono das duas avaliacoes.
--    ATENCAO: hash bcrypt do ambiente de producao. Troque a senha depois
--    de importar, ou ajuste o e-mail se ja existir um user_id=50 local.
-- =====================================================================

INSERT IGNORE INTO `user` (`user_id`,`email`,`username`,`passw`,`type`,`is_verified`,`verification_token`) VALUES
  (50,'casado@gmail.com','casado',_binary '$2b$12$Tf7Sv7ssqcsmBZ70UaaXF.ADLnz8ndxH6FgwhBvQen99eaZWTq.6m','SECO_MANAGER',0,'nlPMIdC9agQBMRbi6D-nJgOifPM_6J-hwed8fCc7gy0');
-- 1 linha(s) em `user`


-- =====================================================================
-- 3) AS DUAS AVALIACOES
-- =====================================================================

INSERT INTO `evaluation` (`evaluation_id`,`name`,`seco_portal`,`seco_portal_url`,`user_id`,`seco_type`,`manager_objective`,`created_at`) VALUES
  (1596077,'pilot test','python','https://www.python.org/',50,'OPEN_SOURCE','we want  to improve our portal transparency','2025-11-11 08:12:56'),
  (2147077,'Lang chain portal evaluation','docs.langchain','https://docs.langchain.com/',50,'HYBRID','Avaliar a eficiência, clareza e navegabilidade da documentação do LangChain, identificando como desenvolvedores de diferentes níveis de experiência compreendem, localizam e aplicam as informações necessárias para construir soluções práticas, medindo barreiras, pontos de fricção e oportunidades de melhoria na experiência do usuário.','2025-11-26 19:37:49');
-- 2 linha(s) em `evaluation`

INSERT INTO `evaluation_SECO_process` (`evaluation_id`,`seco_process_id`) VALUES
  (1596077,1),
  (1596077,2),
  (1596077,3),
  (1596077,4),
  (1596077,5),
  (1596077,6),
  (1596077,7),
  (2147077,1),
  (2147077,2),
  (2147077,3),
  (2147077,5);
-- 11 linha(s) em `evaluation_SECO_process`

INSERT INTO `evaluation_ksc_weight` (`id`,`weight`,`ksc_id`,`evaluation_id`) VALUES
  (62,3,1,1596077),
  (63,2,2,1596077),
  (64,3,3,1596077),
  (65,2,4,1596077),
  (66,3,5,1596077),
  (67,3,6,1596077),
  (68,4,7,1596077),
  (69,2,8,1596077),
  (70,2,9,1596077),
  (71,6,10,1596077),
  (73,2,12,1596077),
  (74,3,13,1596077),
  (75,4,14,1596077),
  (76,3,15,1596077),
  (77,3,16,1596077),
  (78,4,17,1596077),
  (79,4,18,1596077),
  (80,4,19,1596077),
  (81,2,20,1596077),
  (82,1,21,1596077),
  (83,1,22,1596077),
  (84,8,23,1596077),
  (174,3,1,1596077),
  (175,2,2,1596077),
  (176,3,3,1596077),
  (177,2,4,1596077),
  (178,3,5,1596077),
  (179,3,6,1596077),
  (180,4,7,1596077),
  (181,2,8,1596077),
  (182,2,9,1596077),
  (183,6,10,1596077),
  (185,2,12,1596077),
  (186,3,13,1596077),
  (187,4,14,1596077),
  (188,3,15,1596077),
  (189,3,16,1596077),
  (190,4,17,1596077),
  (191,4,18,1596077),
  (192,4,19,1596077);
INSERT INTO `evaluation_ksc_weight` (`id`,`weight`,`ksc_id`,`evaluation_id`) VALUES
  (193,2,20,1596077),
  (194,1,21,1596077),
  (195,1,22,1596077),
  (196,8,23,1596077),
  (255,4,1,2147077),
  (256,3,2,2147077),
  (257,2,3,2147077),
  (258,1,4,2147077),
  (259,5,5,2147077),
  (260,3,6,2147077),
  (261,2,7,2147077),
  (262,5,8,2147077),
  (263,2,9,2147077),
  (264,3,10,2147077),
  (265,4,15,2147077),
  (266,3,16,2147077),
  (267,3,17,2147077),
  (268,4,1,2147077),
  (269,3,2,2147077),
  (270,2,3,2147077),
  (271,1,4,2147077),
  (272,5,5,2147077),
  (273,3,6,2147077),
  (274,2,7,2147077),
  (275,5,8,2147077),
  (276,2,9,2147077),
  (277,3,10,2147077),
  (278,4,15,2147077),
  (279,3,16,2147077),
  (280,3,17,2147077);
-- 70 linha(s) em `evaluation_ksc_weight`


-- =====================================================================
-- 4) SESSOES COLETADAS
--    117 / 119        -> piloto  (1596077)
--    124 / 125 / 126 / 127 -> LangChain (2147077), 4 participantes
-- =====================================================================

INSERT INTO `collected_data` (`collected_data_id`,`start_time`,`end_time`,`evaluation_id`,`cod`,`sessionId`) VALUES
  (117,'2025-11-14 07:01:26','2025-11-14 07:08:45',1596077,'default',0),
  (119,'2025-11-14 14:11:43','2025-11-14 14:13:30',1596077,'1596077-1SVB',81),
  (124,'2025-11-26 19:40:22','2025-11-26 20:11:37',2147077,'2147077-VSK7',88),
  (125,'2025-11-26 19:41:12','2025-11-26 20:11:59',2147077,'2147077-VSK7',88),
  (126,'2025-11-26 19:41:30','2025-11-26 20:18:06',2147077,'2147077-VSK7',88),
  (127,'2025-11-26 19:41:36','2025-11-26 20:18:46',2147077,'2147077-VSK7',88);
-- 6 linha(s) em `collected_data`

INSERT INTO `developer_questionnaire` (`developer_questionnaire_id`,`academic_level`,`previus_xp`,`emotion`,`comments`,`segment`,`experience`,`collected_data_id`) VALUES
  (106,'HIGH_SCHOOL','AWAYS',4,'it was pretty good','ACADEMIA',2,117),
  (108,'MASTER','OFTEN',5,'muito bom teste','BOTH',1,119),
  (113,'MASTER','RARELY',5,'Nada a comentar.','INDUSTRY',10,124),
  (114,'BACHELOR','RARELY',5,'A LangChain segue um padrão de documentação de outros sistemas, com isso fica mais facil de encontrar as informações que eu preciso.','INDUSTRY',4,125),
  (115,'MASTER','RARELY',3,'Para encontrar  as informações de instalação e repositórios foi bem tranquilo. Já as informações de roadmap e contatos ainda está confuso de encontrar.','INDUSTRY',11,126),
  (116,'MASTER','NEVER',4,'Para aspecto de uso e documentação da solução a plataforma LangChain apresenta de forma clara, mas objetivos futuros da plataforma e mapeamento do histórico de desenvolvimento da solução não estava claro (ex: os commits, o histórico de contribuições feitas os merges e decisões futuras da política de uso do software).','BOTH',5,127);
-- 6 linha(s) em `developer_questionnaire`

INSERT INTO `performed_task` (`performed_task_id`,`initial_timestamp`,`final_timestamp`,`status`,`comments`,`collected_data_id`,`task_id`) VALUES
  (591,'2025-11-14 07:01:28','2025-11-14 07:02:42','SOLVED','it was simple',117,1),
  (592,'2025-11-14 07:03:07','2025-11-14 07:03:54','NOT_SURE','im not sure if it was completed',117,2),
  (593,'2025-11-14 07:04:13','2025-11-14 07:05:12','COULDNT_SOLVE','i couldn\'t complete this scenario',117,3),
  (594,'2025-11-14 07:05:35','2025-11-14 07:06:12','NOT_SURE','i\'m not sure',117,4),
  (595,'2025-11-14 07:06:25','2025-11-14 07:06:45','SOLVED','it was pretty easy',117,5),
  (596,'2025-11-14 07:06:58','2025-11-14 07:07:25','SOLVED','it was easy',117,6),
  (597,'2025-11-14 07:07:36','2025-11-14 07:08:18','COULDNT_SOLVE','i couldn\'t comlpete this scenario',117,7),
  (599,'2025-11-14 14:11:44','2025-11-14 14:11:45','SOLVED','teste',119,1),
  (600,'2025-11-14 14:11:56','2025-11-14 14:12:00','NOT_SURE','teset2',119,2),
  (601,'2025-11-14 14:12:15','2025-11-14 14:12:18','SOLVED','vasco',119,3),
  (602,'2025-11-14 14:12:27','2025-11-14 14:12:31','COULDNT_SOLVE','vasco',119,4),
  (603,'2025-11-14 14:12:46','2025-11-14 14:12:50','NOT_SURE','',119,5),
  (604,'2025-11-14 14:12:56','2025-11-14 14:12:58','NOT_SURE','vasco',119,6),
  (605,'2025-11-14 14:13:09','2025-11-14 14:13:13','NOT_SURE','te3ste',119,7),
  (619,'2025-11-26 19:40:28','2025-11-26 19:42:20','SOLVED','O langchain possui uma documentação bem feita. Normalmente não temos dificuldades em configurar o ambiente por ser apenas uma biblioteca. Além disso, quando precisamos de alguma informação mais recente a documentação sempre é bem consistente.',124,1),
  (620,'2025-11-26 19:51:07','2025-11-26 19:51:36','SOLVED','O langchain deixa bem claro onde encontrar os repositórios, no entanto, não permite a visualização dos projetos, históricos de commits e PRs para os usuários da ferramenta.',124,2),
  (621,'2025-11-26 19:57:36','2025-11-26 19:59:26','SOLVED','A plataforma disponibiliza um canal via github aos keystones do projeto. Há espaço para adicionar melhorias, correções, reportar erros e também contribuir.',124,3),
  (622,'2025-11-26 20:05:50','2025-11-26 20:07:59','SOLVED','Foi fácil entender os passos para solicitar a implementação de uma funcionalidade aos desenvolvedores. Eles utilizam a esteira do github. Basicamente é apenas pedir para ser implementada.',124,5),
  (623,'2025-11-26 19:41:32','2025-11-26 19:44:43','SOLVED','A ferramenta e bastante intuitiva para encontrar as informacoes necessarias, principalmente para quem nao conhece, o Quickstart é bem detalhado.',125,1),
  (624,'2025-11-26 19:50:55','2025-11-26 19:54:38','SOLVED','Documentacao bem clara e objetiva para desenvolvedores.',125,2),
  (625,'2025-11-26 19:58:41','2025-11-26 20:00:45','SOLVED','No rodapé do site encontrei com facilidade github dos colaboradores e forum caso eu quisesse verificar se minha duvida ja foi questionada por outros. E tambem a pagina de contribuicoes de bugs e features os colaboradores sao bem ativos para resolver.',125,3),
  (626,'2025-11-26 20:03:30','2025-11-26 20:05:44','SOLVED','O forum é bastante intuitivo e os colaboradores são ativos para responder e resolver as sugestões.',125,5),
  (627,'2025-11-26 19:41:38','2025-11-26 19:44:56','SOLVED','Encontrar as informações iniciais foi bem tranquilo. Acessei a página de Documentações, depois, cliquei em Começar agora > Instalar.',126,1),
  (628,'2025-11-26 19:49:43','2025-11-26 19:56:08','SOLVED','Documentação bem descrita, com todas as informações do repositório e etapas para contribuir e solicitar PRs. Um suporte a outros idiomas seria muito bom para novos desenvolvedores.',126,2),
  (629,'2025-11-26 19:59:57','2025-11-26 20:07:21','SOLVED','Consegui encontrar as páginas de Bugs e contatos. Para mim, não foi tão fácil encontrar as informações solicitadas navegando no portal. precisei usar a barra de pesquisa.',126,3),
  (630,'2025-11-26 20:10:22','2025-11-26 20:14:29','SOLVED','Encontrei algumas informações relacionadas a contribuições e roadmap. Mas, não ficou claro os status de cada decisão e prioridades de implementação.',126,5),
  (631,'2025-11-26 19:42:23','2025-11-26 19:44:36','SOLVED','O LangChain possui a aba de docs explicitamente localizada do lado esquerdo e ao acessar ela direciona para experimentos de instalação e primeiros passos de acordo com a linguagem de programação onde é possível usar as extensões, logo selecionei python pela familiaridade com a linguagem. Logo no overview a documentação ja deixa claro o processo de instalação da biblioteca e a criação do primeiro agent.',127,1),
  (632,'2025-11-26 19:50:43','2025-11-26 19:54:16','SOLVED','O LangChain apresenta o acesso ao gitHub logo de início e como desenvolvedor acessar o GitHub é mais prático para análise de desenvolvimentos feitos no passado além de poder contribuir. Ao voltar para a documentação do LangChain percebi que há uma aba que explica os meio de contribuição e inclusive o pre requisito é o clone do repositório deles no github.',127,2),
  (633,'2025-11-26 19:57:57','2025-11-26 20:00:38','SOLVED','A plataforma do LangChain proporcia o forum, além de uma área para relatar bugs. Além disso, por meio do próprio GitHub é possível acessar informações dos gerenciadores da aplicação e contribuintes.',127,3),
  (634,'2025-11-26 20:04:45','2025-11-26 20:10:31','NOT_SURE','A plataforma do Lang Chain não deixa claro os próximos objetivos e decisões gerenciais. Não estava claro na página principal, mas algumas informações estão mais apresentadas no github do LangChain e não na página principal.',127,5);
-- 30 linha(s) em `performed_task`

INSERT INTO `answer` (`answer_id`,`answer`,`collected_data_id`,`question_id`) VALUES
  (1601,19,117,1),
  (1602,79,117,2),
  (1603,100,117,3),
  (1604,0,117,4),
  (1605,100,117,5),
  (1606,100,117,6),
  (1607,27,117,7),
  (1608,33,117,8),
  (1609,14,117,9),
  (1610,92,117,10),
  (1611,84,117,12),
  (1612,11,117,13),
  (1613,100,117,14),
  (1614,60,117,15),
  (1615,99,117,16),
  (1616,100,117,17),
  (1617,100,117,18),
  (1618,100,117,19),
  (1619,70,117,20),
  (1620,10,117,21),
  (1621,33,117,22),
  (1622,100,117,23),
  (1627,26,119,1),
  (1628,12,119,2),
  (1629,14,119,3),
  (1630,13,119,4),
  (1631,88,119,5),
  (1632,73,119,6),
  (1633,82,119,7),
  (1634,26,119,8),
  (1635,33,119,9),
  (1636,23,119,10),
  (1637,100,119,12),
  (1638,89,119,13),
  (1639,90,119,14),
  (1640,95,119,15),
  (1641,81,119,16),
  (1642,80,119,17),
  (1643,82,119,18),
  (1644,86,119,19),
  (1645,83,119,20),
  (1646,100,119,21),
  (1647,100,119,22),
  (1648,100,119,23),
  (1692,100,124,1),
  (1693,100,124,2),
  (1694,100,124,3),
  (1695,48,124,4),
  (1696,100,124,5),
  (1697,0,124,6),
  (1698,0,124,7),
  (1699,100,124,8),
  (1700,100,124,9),
  (1701,100,124,10),
  (1702,100,124,15),
  (1703,80,124,16),
  (1704,27,124,17),
  (1705,95,125,1),
  (1706,79,125,2),
  (1707,85,125,3);
INSERT INTO `answer` (`answer_id`,`answer`,`collected_data_id`,`question_id`) VALUES
  (1708,92,125,4),
  (1709,88,125,5),
  (1710,91,125,6),
  (1711,77,125,7),
  (1712,100,125,8),
  (1713,94,125,9),
  (1714,92,125,10),
  (1715,93,125,15),
  (1716,89,125,16),
  (1717,90,125,17),
  (1718,38,126,1),
  (1719,56,126,2),
  (1720,59,126,3),
  (1721,60,126,4),
  (1722,60,126,5),
  (1723,50,126,6),
  (1724,40,126,7),
  (1725,19,126,8),
  (1726,39,126,9),
  (1727,17,126,10),
  (1728,32,126,15),
  (1729,38,126,16),
  (1730,35,126,17),
  (1731,100,127,1),
  (1732,82,127,2),
  (1733,62,127,3),
  (1734,80,127,4),
  (1735,100,127,5),
  (1736,98,127,6),
  (1737,89,127,7),
  (1738,94,127,8),
  (1739,78,127,9),
  (1740,31,127,10),
  (1741,40,127,15),
  (1742,44,127,16),
  (1743,44,127,17);
-- 96 linha(s) em `answer`

INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (127,'PAGE_NAVIGATION','Home Page','http://127.0.0.1:5000/','2025-11-14 07:01:28',1,117),
  (128,'PAGE_NAVIGATION','Documentation','http://127.0.0.1:5000/doc','2025-11-14 07:01:57',1,117),
  (129,'PAGE_NAVIGATION','About','http://127.0.0.1:5000/about','2025-11-14 07:02:18',1,117),
  (130,'PAGE_NAVIGATION','About','http://127.0.0.1:5000/about','2025-11-14 07:03:07',2,117),
  (131,'PAGE_NAVIGATION','Guidelines','http://127.0.0.1:5000/guidelines','2025-11-14 07:03:13',2,117),
  (132,'PAGE_NAVIGATION','Guidelines','http://127.0.0.1:5000/guidelines','2025-11-14 07:04:13',3,117),
  (133,'PAGE_NAVIGATION','Home Page','http://127.0.0.1:5000/','2025-11-14 07:04:18',3,117),
  (134,'PAGE_NAVIGATION','Documentation','http://127.0.0.1:5000/doc','2025-11-14 07:04:28',3,117),
  (135,'PAGE_NAVIGATION','Home Page','http://127.0.0.1:5000/','2025-11-14 07:04:32',3,117),
  (136,'PAGE_NAVIGATION','Home Page','http://127.0.0.1:5000/#aboutlink','2025-11-14 07:04:46',3,117),
  (137,'PAGE_NAVIGATION','Evaluations','http://127.0.0.1:5000/evaluations','2025-11-14 07:04:51',3,117),
  (138,'PAGE_NAVIGATION','Documentation','http://127.0.0.1:5000/doc','2025-11-14 07:04:56',3,117),
  (139,'PAGE_NAVIGATION','Downloads','http://127.0.0.1:5000/downloads','2025-11-14 07:04:58',3,117),
  (140,'PAGE_NAVIGATION','Downloads','http://127.0.0.1:5000/downloads','2025-11-14 07:05:35',4,117),
  (141,'PAGE_NAVIGATION','About','http://127.0.0.1:5000/about','2025-11-14 07:05:39',4,117),
  (142,'PAGE_NAVIGATION','About','http://127.0.0.1:5000/about','2025-11-14 07:06:25',5,117),
  (143,'PAGE_NAVIGATION','Documentation','http://127.0.0.1:5000/doc','2025-11-14 07:06:27',5,117),
  (144,'PAGE_NAVIGATION','Documentation','http://127.0.0.1:5000/doc#dashboard','2025-11-14 07:06:32',5,117),
  (145,'PAGE_NAVIGATION','Documentation','http://127.0.0.1:5000/doc#glossary','2025-11-14 07:06:34',5,117),
  (146,'PAGE_NAVIGATION','Documentation','http://127.0.0.1:5000/doc#evaluationflow','2025-11-14 07:06:35',5,117),
  (147,'PAGE_NAVIGATION','Documentation','http://127.0.0.1:5000/doc#introduction','2025-11-14 07:06:41',5,117),
  (148,'PAGE_NAVIGATION','Documentation','http://127.0.0.1:5000/doc#introduction','2025-11-14 07:06:58',6,117),
  (149,'PAGE_NAVIGATION','Guidelines','http://127.0.0.1:5000/guidelines','2025-11-14 07:07:02',6,117),
  (150,'PAGE_NAVIGATION','Guidelines','http://127.0.0.1:5000/guidelines','2025-11-14 07:07:36',7,117),
  (151,'PAGE_NAVIGATION','Home Page','http://127.0.0.1:5000/','2025-11-14 07:07:41',7,117),
  (161,'PAGE_NAVIGATION','Evaluations','https://seco-tranp-website.vercel.app/evaluations','2025-11-14 14:11:44',1,119),
  (162,'PAGE_NAVIGATION','Home Page','https://seco-tranp-website.vercel.app/','2025-11-14 14:11:48',1,119),
  (163,'PAGE_NAVIGATION','Home Page','https://seco-tranp-website.vercel.app/','2025-11-14 14:11:56',2,119),
  (164,'PAGE_NAVIGATION','Downloads','https://seco-tranp-website.vercel.app/downloads','2025-11-14 14:11:58',2,119),
  (165,'PAGE_NAVIGATION','Guidelines','https://seco-tranp-website.vercel.app/guidelines','2025-11-14 14:12:15',3,119);
INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (166,'PAGE_NAVIGATION','Guidelines','https://seco-tranp-website.vercel.app/guidelines','2025-11-14 14:12:27',4,119),
  (167,'PAGE_NAVIGATION','Evaluations','https://seco-tranp-website.vercel.app/evaluations','2025-11-14 14:12:29',4,119),
  (168,'PAGE_NAVIGATION','Home Page','https://seco-tranp-website.vercel.app/','2025-11-14 14:12:46',5,119),
  (169,'PAGE_NAVIGATION','Evaluations','https://seco-tranp-website.vercel.app/evaluations','2025-11-14 14:12:56',6,119),
  (170,'PAGE_NAVIGATION','Home Page','https://seco-tranp-website.vercel.app/','2025-11-14 14:13:09',7,119),
  (171,'PAGE_NAVIGATION','Home Page','https://seco-tranp-website.vercel.app/#aboutlink','2025-11-14 14:13:11',7,119),
  (242,'PAGE_NAVIGATION','Extensões','chrome://extensions/','2025-11-26 19:40:28',1,124),
  (243,'TAB_SWITCH','Chat | Estudo de portais de ECOS | Microsoft Teams','https://teams.microsoft.com/v2/','2025-11-26 19:40:48',1,124),
  (244,'PAGE_NAVIGATION','Verificando o link','https://statics.teams.cdn.office.net/evergreen-assets/safelinks/2/atp-safelinks.html','2025-11-26 19:40:53',1,124),
  (245,'TAB_SWITCH','Chat | Estudo de portais de ECOS | Microsoft Teams','https://teams.microsoft.com/v2/','2025-11-26 19:40:54',1,124),
  (246,'TAB_SWITCH','Verificando o link','https://statics.teams.cdn.office.net/evergreen-assets/safelinks/2/atp-safelinks.html','2025-11-26 19:40:54',1,124),
  (247,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*1huwafk*_gcl_au*MTc0Mjc2NTYwMy4xNzY0MTg0MzQx*_ga*NzA2NjQ1OTMxLjE3','2025-11-26 19:40:57',1,124),
  (248,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*1huwafk*_gcl_au*MTc0Mjc2NTYwMy4xNzY0MTg0MzQx*_ga*NzA2NjQ1OTMxLjE3','2025-11-26 19:43:07',1,124),
  (249,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/tag/self-hosted','2025-11-26 19:43:18',1,124),
  (250,'PAGE_NAVIGATION','Latest self-hosted topics - LangChain Forum','https://forum.langchain.com/tags','2025-11-26 19:43:35',1,124),
  (251,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/?_gl=1*b2c1js*_gcl_au*NzM1ODI2Nzg3LjE3NjQxODYxODY.*_ga*MjE5NTM5MTMxLjE3Nj','2025-11-26 19:43:48',1,124),
  (252,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/oss/python/langgraph/overview','2025-11-26 19:43:53',1,124),
  (253,'PAGE_NAVIGATION','LangGraph overview - Docs by LangChain','https://docs.langchain.com/oss/python/langgraph/quickstart','2025-11-26 19:43:56',1,124),
  (254,'PAGE_NAVIGATION','Quickstart - Docs by LangChain','https://docs.langchain.com/oss/python/langgraph/install','2025-11-26 19:44:04',1,124),
  (255,'PAGE_NAVIGATION','Install LangGraph - Docs by LangChain','https://docs.langchain.com/oss/python/langgraph/quickstart','2025-11-26 19:44:15',1,124),
  (256,'PAGE_NAVIGATION','Quickstart - Docs by LangChain','https://docs.langchain.com/oss/python/langgraph/local-server','2025-11-26 19:44:22',1,124),
  (257,'TAB_SWITCH','Nova guia','chrome://newtab/','2025-11-26 19:48:03',1,124),
  (258,'PAGE_NAVIGATION','Nova guia','chrome://newtab/','2025-11-26 19:48:03',1,124),
  (259,'PAGE_NAVIGATION','Outrossim - Pesquisa Google','https://www.google.com/search?q=Outrossim&oq=Outrossim&gs_lcrp=EgZjaHJvbWUyBggAEEUYOdIBBzE4M2owajeoA','2025-11-26 19:48:05',1,124),
  (260,'TAB_SWITCH','Run a local server - Docs by LangChain','https://docs.langchain.com/oss/python/langgraph/local-server','2025-11-26 19:48:10',1,124),
  (261,'PAGE_NAVIGATION','Run a local server - Docs by LangChain','https://docs.langchain.com/oss/python/langgraph/local-server','2025-11-26 19:51:07',2,124),
  (262,'PAGE_NAVIGATION','LangChain · GitHub','https://github.com/langchain-ai','2025-11-26 19:51:45',2,124),
  (263,'PAGE_NAVIGATION','langchain-ai repositories · GitHub','https://github.com/orgs/langchain-ai/repositories','2025-11-26 19:52:18',2,124),
  (264,'PAGE_NAVIGATION','LangChain · GitHub','https://github.com/langchain-ai','2025-11-26 19:52:33',2,124),
  (265,'PAGE_NAVIGATION','langchain-ai repositories · GitHub','https://github.com/orgs/langchain-ai/repositories','2025-11-26 19:52:34',2,124);
INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (266,'PAGE_NAVIGATION','langchain-ai repositories · GitHub','https://github.com/orgs/langchain-ai/repositories?q=visibility%3Apublic+archived%3Afalse','2025-11-26 19:52:40',2,124),
  (267,'PAGE_NAVIGATION','langchain-ai repositories · GitHub','https://github.com/orgs/langchain-ai/repositories?q=mirror%3Afalse+fork%3Afalse+archived%3Afalse','2025-11-26 19:52:42',2,124),
  (268,'PAGE_NAVIGATION','langchain-ai repositories · GitHub','https://github.com/orgs/langchain-ai/repositories?q=fork%3Atrue+archived%3Afalse','2025-11-26 19:52:47',2,124),
  (269,'PAGE_NAVIGATION','Packages · LangChain · GitHub','https://github.com/orgs/langchain-ai/packages','2025-11-26 19:52:55',2,124),
  (270,'PAGE_NAVIGATION','Members · People · langchain-ai · GitHub','https://github.com/orgs/langchain-ai/people','2025-11-26 19:54:19',2,124),
  (271,'PAGE_NAVIGATION','Packages · LangChain · GitHub','https://github.com/orgs/langchain-ai/packages','2025-11-26 19:54:27',2,124),
  (272,'PAGE_NAVIGATION','langchain-ai repositories · GitHub','https://github.com/orgs/langchain-ai/repositories','2025-11-26 19:54:34',2,124),
  (273,'PAGE_NAVIGATION','LangChain · GitHub','https://github.com/langchain-ai','2025-11-26 19:54:36',2,124),
  (274,'PAGE_NAVIGATION','langchain-ai repositories · GitHub','https://github.com/orgs/langchain-ai/repositories','2025-11-26 19:55:46',2,124),
  (275,'PAGE_NAVIGATION','Projects · langchain-ai · GitHub','https://github.com/orgs/langchain-ai/projects?query=is%3Aopen','2025-11-26 19:55:49',2,124),
  (276,'PAGE_NAVIGATION','Projects · langchain-ai · GitHub','https://github.com/orgs/langchain-ai/projects?query=is%3Aopen+is%3Atemplate','2025-11-26 19:55:52',2,124),
  (277,'PAGE_NAVIGATION','Projects · langchain-ai · GitHub','https://github.com/orgs/langchain-ai/projects?query=is%3Aopen','2025-11-26 19:55:53',2,124),
  (278,'PAGE_NAVIGATION','Projects · langchain-ai · GitHub','https://github.com/orgs/langchain-ai/projects?query=is%3Aopen','2025-11-26 19:57:36',3,124),
  (279,'TAB_SWITCH','Nova guia','chrome://newtab/','2025-11-26 19:57:44',3,124),
  (280,'PAGE_NAVIGATION','Keystone - Pesquisa Google','https://www.google.com/search?q=Keystone&oq=Keystone&gs_lcrp=EgZjaHJvbWUyDAgAEEUYORixAxiABDIKCAEQABi','2025-11-26 19:57:48',3,124),
  (281,'TAB_SWITCH','Projects · langchain-ai · GitHub','https://github.com/orgs/langchain-ai/projects?query=is%3Aopen','2025-11-26 19:57:59',3,124),
  (282,'TAB_SWITCH','Run a local server - Docs by LangChain','https://docs.langchain.com/oss/python/langgraph/local-server','2025-11-26 19:58:13',3,124),
  (283,'PAGE_NAVIGATION','Run a local server - Docs by LangChain','https://docs.langchain.com/','2025-11-26 19:58:15',3,124),
  (284,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/','2025-11-26 19:59:15',3,124),
  (285,'PAGE_NAVIGATION','Run a local server - Docs by LangChain','https://docs.langchain.com/oss/python/langgraph/local-server','2025-11-26 19:59:17',3,124),
  (286,'PAGE_NAVIGATION','Run a local server - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 19:59:21',3,124),
  (287,'PAGE_NAVIGATION','LangChain · GitHub','https://github.com/langchain-ai','2025-11-26 20:00:25',3,124),
  (288,'PAGE_NAVIGATION','langchain-ai repositories · GitHub','https://github.com/orgs/langchain-ai/repositories','2025-11-26 20:00:36',3,124),
  (289,'PAGE_NAVIGATION','LangChain · GitHub','https://github.com/langchain-ai','2025-11-26 20:00:42',3,124),
  (290,'PAGE_NAVIGATION','Members · People · langchain-ai · GitHub','https://github.com/orgs/langchain-ai/people','2025-11-26 20:00:45',3,124),
  (291,'TAB_SWITCH','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 20:00:50',3,124),
  (292,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/learn','2025-11-26 20:00:56',3,124),
  (293,'PAGE_NAVIGATION','Learn - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview','2025-11-26 20:00:58',3,124),
  (294,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#contribute-code','2025-11-26 20:01:08',3,124),
  (295,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#report-bugs','2025-11-26 20:01:12',3,124);
INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (296,'PAGE_NAVIGATION','Issues · langchain-ai/langchain · GitHub','https://github.com/langchain-ai/langchain/issues','2025-11-26 20:01:19',3,124),
  (297,'PAGE_NAVIGATION','Sign in to GitHub · GitHub','https://github.com/login?return_to=https://github.com/langchain-ai/langchain/issues','2025-11-26 20:01:39',3,124),
  (298,'PAGE_NAVIGATION','Issues · langchain-ai/langchain · GitHub','https://github.com/langchain-ai/langchain/issues','2025-11-26 20:01:43',3,124),
  (299,'TAB_SWITCH','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#report-bugs','2025-11-26 20:02:04',3,124),
  (300,'PAGE_NAVIGATION','Issues · langchain-ai/langgraph · GitHub','https://github.com/langchain-ai/langgraph/issues','2025-11-26 20:02:10',3,124),
  (301,'TAB_SWITCH','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#report-bugs','2025-11-26 20:02:12',3,124),
  (302,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#suggest-features','2025-11-26 20:02:14',3,124),
  (303,'PAGE_NAVIGATION','Issues · langchain-ai/langchain · GitHub','https://github.com/langchain-ai/langchain/issues?q=state%3Aopen%20label%3A%22feature%20request%22','2025-11-26 20:02:20',3,124),
  (304,'TAB_SWITCH','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#suggest-features','2025-11-26 20:02:34',3,124),
  (305,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview','2025-11-26 20:02:36',3,124),
  (306,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#contribute-code','2025-11-26 20:02:37',3,124),
  (307,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/code','2025-11-26 20:02:38',3,124),
  (308,'TAB_SWITCH','Projects · langchain-ai · GitHub','https://github.com/orgs/langchain-ai/projects?query=is%3Aopen','2025-11-26 20:05:47',5,124),
  (309,'TAB_SWITCH','Issues · langchain-ai/langchain · GitHub','https://github.com/langchain-ai/langchain/issues','2025-11-26 20:05:48',5,124),
  (310,'PAGE_NAVIGATION','Issues · langchain-ai/langchain · GitHub','https://github.com/langchain-ai/langchain/issues','2025-11-26 20:05:50',5,124),
  (311,'TAB_SWITCH','LangChain · GitHub','https://github.com/langchain-ai','2025-11-26 20:06:53',5,124),
  (312,'PAGE_NAVIGATION','Nova guia','chrome://newtab/','2025-11-26 20:06:55',5,124),
  (313,'PAGE_NAVIGATION','portal freely - Pesquisa Google','https://www.google.com/search?q=portal+freely&oq=portal+freely&gs_lcrp=EgZjaHJvbWUyBggAEEUYOTIHCAEQI','2025-11-26 20:06:56',5,124),
  (314,'PAGE_NAVIGATION','Traduza texto e documentos de forma instantânea. Traduções precisas para usuários únicos ou equipes.','https://www.deepl.com/pt-BR/translator','2025-11-26 20:07:02',5,124),
  (315,'TAB_SWITCH','Issues · langchain-ai/langchain · GitHub','https://github.com/langchain-ai/langchain/issues?q=state%3Aopen%20label%3A%22feature%20request%22','2025-11-26 20:07:12',5,124),
  (316,'TAB_SWITCH','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/code','2025-11-26 20:07:13',5,124),
  (317,'TAB_SWITCH','Issues · langchain-ai/langchain · GitHub','https://github.com/langchain-ai/langchain/issues?q=state%3Aopen%20label%3A%22feature%20request%22','2025-11-26 20:07:52',5,124),
  (318,'TAB_SWITCH','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/code','2025-11-26 20:07:54',5,124),
  (319,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#contribute-code','2025-11-26 20:08:21',5,124),
  (320,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#suggest-features','2025-11-26 20:08:26',5,124),
  (321,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/','2025-11-26 19:41:32',1,125),
  (322,'PAGE_NAVIGATION','Google Translate','https://translate.google.com/?sl=auto&tl=en&text=Imagine%20that%20you%20have%20just%20joined%20a%20p','2025-11-26 19:43:20',1,125),
  (323,'PAGE_NAVIGATION','Google Translate','https://translate.google.com/?sl=auto&tl=pt&text=Imagine%20that%20you%20have%20just%20joined%20a%20p','2025-11-26 19:43:25',1,125),
  (324,'TAB_SWITCH','LangChain Forum','https://forum.langchain.com/','2025-11-26 19:43:54',1,125),
  (325,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/?_gl=1*14rvwdi*_ga*MTY3NDcyOTU0MC4xNzY0MTg0NzEx*_ga_47WX3HKKY2*czE3NjQxOD','2025-11-26 19:44:04',1,125);
INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (326,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/?_gl=1*14rvwdi*_ga*MTY3NDcyOTU0MC4xNzY0MTg0NzEx*_ga_47WX3HKKY2*czE3NjQxOD','2025-11-26 19:44:21',1,125),
  (327,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/overview','2025-11-26 19:44:33',1,125),
  (328,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/middleware/overview','2025-11-26 19:45:53',1,125),
  (329,'PAGE_NAVIGATION','Overview - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/install','2025-11-26 19:46:02',1,125),
  (330,'PAGE_NAVIGATION','Install LangChain - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/quickstart','2025-11-26 19:46:08',1,125),
  (331,'PAGE_NAVIGATION','Agents - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/agents','2025-11-26 19:50:55',2,125),
  (332,'PAGE_NAVIGATION','Agents - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/models','2025-11-26 19:52:19',2,125),
  (333,'PAGE_NAVIGATION','Models - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/messages','2025-11-26 19:52:20',2,125),
  (334,'PAGE_NAVIGATION','Messages - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/tools','2025-11-26 19:52:22',2,125),
  (335,'PAGE_NAVIGATION','Tools - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/tools','2025-11-26 19:52:26',2,125),
  (336,'PAGE_NAVIGATION','Tools - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/deploy','2025-11-26 19:52:41',2,125),
  (337,'PAGE_NAVIGATION','GitHub','https://github.com/','2025-11-26 19:52:52',2,125),
  (338,'TAB_SWITCH','LangSmith Deployment - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/deploy','2025-11-26 19:52:58',2,125),
  (339,'TAB_SWITCH','GitHub','https://github.com/','2025-11-26 19:53:01',2,125),
  (340,'TAB_SWITCH','LangSmith Deployment - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/deploy','2025-11-26 19:53:04',2,125),
  (341,'PAGE_NAVIGATION','LangSmith Deployment - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/deploy','2025-11-26 19:53:11',2,125),
  (342,'PAGE_NAVIGATION','LangSmith','https://smith.langchain.com/?_gl=1*1dwypgm*_gcl_au*MTQzMjg5MzE2MC4xNzY0MTg2MjQz*_ga*MTY3NDcyOTU0MC4x','2025-11-26 19:53:20',2,125),
  (343,'TAB_SWITCH','LangSmith Deployment - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/deploy','2025-11-26 19:53:38',2,125),
  (344,'PAGE_NAVIGATION','LangSmith Deployment - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/overview','2025-11-26 19:53:58',2,125),
  (345,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/javascript/learn','2025-11-26 19:54:00',2,125),
  (346,'PAGE_NAVIGATION','Learn - Docs by LangChain','https://docs.langchain.com/oss/javascript/reference/overview','2025-11-26 19:54:11',2,125),
  (347,'PAGE_NAVIGATION','Reference - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/overview','2025-11-26 19:54:23',2,125),
  (348,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/overview#contribute-code','2025-11-26 19:54:28',2,125),
  (349,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/javascript/langgraph/overview','2025-11-26 19:54:33',2,125),
  (350,'PAGE_NAVIGATION','LangGraph overview - Docs by LangChain','https://docs.langchain.com/oss/javascript/langchain/overview','2025-11-26 19:55:27',2,125),
  (351,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/overview','2025-11-26 19:55:36',2,125),
  (352,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/documentation','2025-11-26 19:55:44',2,125),
  (353,'PAGE_NAVIGATION','Contributing to documentation - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/code','2025-11-26 19:55:58',2,125),
  (354,'PAGE_NAVIGATION','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/code#repository-structure','2025-11-26 19:56:11',2,125),
  (355,'PAGE_NAVIGATION','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/code#repository-structure','2025-11-26 19:58:41',3,125);
INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (356,'PAGE_NAVIGATION','LangChain','https://github.com/langchain-ai','2025-11-26 19:59:54',3,125),
  (357,'TAB_SWITCH','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/code#repository-structure','2025-11-26 20:00:05',3,125),
  (358,'TAB_SWITCH','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/code#repository-structure','2025-11-26 20:00:16',3,125),
  (359,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*1fy6tmy*_gcl_au*MTQzMjg5MzE2MC4xNzY0MTg2MjQz*_ga*MTY3NDcyOTU0MC4x','2025-11-26 20:00:25',3,125),
  (360,'TAB_SWITCH','LangChain','https://github.com/langchain-ai','2025-11-26 20:00:33',3,125),
  (361,'PAGE_NAVIGATION','LangChain','https://github.com/langchain-ai','2025-11-26 20:03:30',5,125),
  (362,'TAB_SWITCH','LangChain Forum','https://forum.langchain.com/?_gl=1*1fy6tmy*_gcl_au*MTQzMjg5MzE2MC4xNzY0MTg2MjQz*_ga*MTY3NDcyOTU0MC4x','2025-11-26 20:04:07',5,125),
  (363,'TAB_SWITCH','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/code#repository-structure','2025-11-26 20:04:22',5,125),
  (364,'TAB_SWITCH','LangChain Forum','https://forum.langchain.com/?_gl=1*1fy6tmy*_gcl_au*MTQzMjg5MzE2MC4xNzY0MTg2MjQz*_ga*MTY3NDcyOTU0MC4x','2025-11-26 20:04:56',5,125),
  (365,'PAGE_NAVIGATION','Open Source Contribution to langchain - Talking Shop - LangChain Forum','https://forum.langchain.com/t/open-source-contribution-to-langchain/1049','2025-11-26 20:05:10',5,125),
  (366,'PAGE_NAVIGATION','langchain-xai: `test_serdes` fails due to protocol changes · Issue #32173 · langchain-ai/langchain','https://github.com/langchain-ai/langchain/issues/32173','2025-11-26 20:05:25',5,125),
  (367,'PAGE_NAVIGATION','Pull requests · langchain-ai/langchain','https://github.com/langchain-ai/langchain/pulls','2025-11-26 20:05:39',5,125),
  (368,'PAGE_NAVIGATION','Pull requests · langchain-ai/langchain','https://github.com/langchain-ai/langchain/issues','2025-11-26 20:05:43',5,125),
  (369,'TAB_SWITCH','LangChain','https://github.com/langchain-ai','2025-11-26 20:06:26',5,125),
  (370,'TAB_SWITCH','GitHub · Where software is built','https://github.com/langchain-ai/langchain/issues','2025-11-26 20:06:51',5,125),
  (371,'TAB_SWITCH','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/code#repository-structure','2025-11-26 20:07:33',5,125),
  (372,'PAGE_NAVIGATION','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/javascript/contributing/code#development-workflow','2025-11-26 20:07:46',5,125),
  (373,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*1huwafk*_gcl_au*MTc0Mjc2NTYwMy4xNzY0MTg0MzQx*_ga*NzA2NjQ1OTMxLjE3','2025-11-26 19:41:38',1,126),
  (374,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/?_gl=1*4s7j62*_ga*MTQzNjE3NDUzLjE3NjQxODUxODE.*_ga_47WX3HKKY2*czE3NjQxODU','2025-11-26 19:43:32',1,126),
  (375,'PAGE_NAVIGATION','Página inicial - Documentação por LangChain','https://docs.langchain.com/oss/python/langchain/quickstart','2025-11-26 19:44:07',1,126),
  (376,'PAGE_NAVIGATION','Guia de início rápido - Documentação da LangChain','https://docs.langchain.com/oss/python/langchain/install','2025-11-26 19:44:36',1,126),
  (377,'PAGE_NAVIGATION','Install LangChain - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/install','2025-11-26 19:49:43',2,126),
  (378,'PAGE_NAVIGATION','Install LangChain - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/deploy','2025-11-26 19:52:33',2,126),
  (379,'PAGE_NAVIGATION','LangSmith Deployment - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview','2025-11-26 19:54:12',2,126),
  (380,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#contribute-code','2025-11-26 19:54:27',2,126),
  (381,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/code','2025-11-26 19:54:43',2,126),
  (382,'PAGE_NAVIGATION','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/code','2025-11-26 19:59:57',3,126),
  (383,'PAGE_NAVIGATION','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 20:00:58',3,126),
  (384,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*13i8m96*_gcl_au*ODUwMDgxOTQ1LjE3NjQxODYyMDY.*_ga*MTQzNjE3NDUzLjE3','2025-11-26 20:01:13',3,126),
  (385,'PAGE_NAVIGATION','LangChain Support Portal','https://support.langchain.com/?_gl=1*ov95lf*_gcl_au*ODUwMDgxOTQ1LjE3NjQxODYyMDY.*_ga*MTQzNjE3NDUzLjE','2025-11-26 20:01:23',3,126);
INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (386,'PAGE_NAVIGATION','LangChain Support Portal','https://support.langchain.com/?_gl=1*ov95lf*_gcl_au*ODUwMDgxOTQ1LjE3NjQxODYyMDY.*_ga*MTQzNjE3NDUzLjE','2025-11-26 20:01:23',3,126),
  (387,'TAB_SWITCH','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 20:01:48',3,126),
  (388,'PAGE_NAVIGATION','Vanta','https://trust.langchain.com/?_gl=1*1bo2y64*_gcl_au*ODUwMDgxOTQ1LjE3NjQxODYyMDY.*_ga*MTQzNjE3NDUzLjE3','2025-11-26 20:02:04',3,126),
  (389,'TAB_SWITCH','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 20:02:07',3,126),
  (390,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/releases/changelog','2025-11-26 20:02:16',3,126),
  (391,'PAGE_NAVIGATION','Changelog - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview','2025-11-26 20:02:19',3,126),
  (392,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/reference/overview','2025-11-26 20:02:20',3,126),
  (393,'PAGE_NAVIGATION','Reference - Docs by LangChain','https://docs.langchain.com/','2025-11-26 20:02:24',3,126),
  (394,'PAGE_NAVIGATION','LangChain','https://www.langchain.com/','2025-11-26 20:02:34',3,126),
  (395,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/','2025-11-26 20:02:56',3,126),
  (396,'TAB_SWITCH','Home - Docs by LangChain','https://docs.langchain.com/','2025-11-26 20:03:19',3,126),
  (397,'TAB_SWITCH','Home - Docs by LangChain','https://docs.langchain.com/','2025-11-26 20:03:23',3,126),
  (398,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/quickstart','2025-11-26 20:03:44',3,126),
  (399,'PAGE_NAVIGATION','Quickstart - Docs by LangChain','https://docs.langchain.com/oss/python/releases/changelog','2025-11-26 20:03:46',3,126),
  (400,'PAGE_NAVIGATION','Changelog - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#report-bugs','2025-11-26 20:04:06',3,126),
  (401,'PAGE_NAVIGATION','Issues · langchain-ai/langchain · GitHub','https://github.com/langchain-ai/langchain/issues','2025-11-26 20:04:23',3,126),
  (402,'TAB_SWITCH','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#report-bugs','2025-11-26 20:04:23',3,126),
  (403,'TAB_SWITCH','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#report-bugs','2025-11-26 20:04:28',3,126),
  (404,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/comarketing','2025-11-26 20:04:53',3,126),
  (405,'PAGE_NAVIGATION','Co-marketing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/documentation','2025-11-26 20:05:00',3,126),
  (406,'PAGE_NAVIGATION','Contributing to documentation - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview','2025-11-26 20:05:01',3,126),
  (407,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#report-bugs','2025-11-26 20:05:04',3,126),
  (408,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#improve-documentation','2025-11-26 20:05:31',3,126),
  (409,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#contribute-code','2025-11-26 20:05:33',3,126),
  (410,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview#add-a-new-integration','2025-11-26 20:05:35',3,126),
  (411,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/documentation','2025-11-26 20:06:14',3,126),
  (412,'PAGE_NAVIGATION','Contributing to documentation - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/code','2025-11-26 20:06:54',3,126),
  (413,'PAGE_NAVIGATION','Contributing to code - Docs by LangChain','https://docs.langchain.com/langsmith/pricing-faq#frequently-asked-questions','2025-11-26 20:08:04',3,126),
  (414,'PAGE_NAVIGATION','Frequently Asked Questions - Docs by LangChain','https://docs.langchain.com/langsmith/pricing-faq#frequently-asked-questions','2025-11-26 20:10:22',5,126),
  (415,'PAGE_NAVIGATION','Frequently Asked Questions - Docs by LangChain','https://docs.langchain.com/langsmith/faq','2025-11-26 20:11:28',5,126);
INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (416,'PAGE_NAVIGATION','Frequently asked questions - Docs by LangChain','https://docs.langchain.com/langsmith/agent-server-changelog','2025-11-26 20:11:34',5,126),
  (417,'PAGE_NAVIGATION','Agent Server changelog - Docs by LangChain','https://docs.langchain.com/langsmith/release-versions','2025-11-26 20:11:45',5,126),
  (418,'PAGE_NAVIGATION','Release versions - Docs by LangChain','https://docs.langchain.com/langsmith/deployments','2025-11-26 20:12:02',5,126),
  (419,'PAGE_NAVIGATION','LangSmith Deployment - Docs by LangChain','https://docs.langchain.com/langsmith/prompt-engineering','2025-11-26 20:12:36',5,126),
  (420,'PAGE_NAVIGATION','Prompt engineering - Docs by LangChain','https://docs.langchain.com/langsmith/evaluation','2025-11-26 20:12:37',5,126),
  (421,'PAGE_NAVIGATION','LangSmith Evaluations - Docs by LangChain','https://docs.langchain.com/langsmith/observability','2025-11-26 20:12:37',5,126),
  (422,'PAGE_NAVIGATION','LangSmith Observability - Docs by LangChain','https://docs.langchain.com/langsmith/home','2025-11-26 20:12:38',5,126),
  (423,'PAGE_NAVIGATION','LangSmith docs - Docs by LangChain','https://docs.langchain.com/langsmith/deployments','2025-11-26 20:12:50',5,126),
  (424,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*1caf97m*_gcl_au*ODUwMDgxOTQ1LjE3NjQxODYyMDY.*_ga*MTQzNjE3NDUzLjE3','2025-11-26 20:13:13',5,126),
  (425,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/c/announcements/15','2025-11-26 20:13:45',5,126),
  (426,'PAGE_NAVIGATION','Latest Announcements topics - LangChain Forum','https://forum.langchain.com/c/help/langsmith/8','2025-11-26 20:14:01',5,126),
  (427,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/?_gl=1*t9rm0y*_gcl_au*ODUwMDgxOTQ1LjE3NjQxODYyMDY.*_ga*MTQzNjE3NDUzLjE3Nj','2025-11-26 20:14:53',5,126),
  (428,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/?_gl=1*1x9pu5j*_ga*NTQ3OTY0MDUzLjE3NjQxODUyMjc.*_ga_47WX3HKKY2*czE3NjQxOD','2025-11-26 19:41:45',1,127),
  (429,'PAGE_NAVIGATION','Latest OSS Product Help/LangGraph topics - LangChain Forum','https://forum.langchain.com/c/oss-product-help-lc-and-lg/langgraph/13','2025-11-26 19:41:54',1,127),
  (430,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*1huwafk*_gcl_au*MTc0Mjc2NTYwMy4xNzY0MTg0MzQx*_ga*NzA2NjQ1OTMxLjE3','2025-11-26 19:41:56',1,127),
  (431,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*1huwafk*_gcl_au*MTc0Mjc2NTYwMy4xNzY0MTg0MzQx*_ga*NzA2NjQ1OTMxLjE3','2025-11-26 19:42:23',1,127),
  (432,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/?_gl=1*s3vrw3*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLjE3Nj','2025-11-26 19:43:31',1,127),
  (433,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 19:44:00',1,127),
  (434,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview#install','2025-11-26 19:45:37',1,127),
  (435,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview#create-an-agent','2025-11-26 19:45:41',1,127),
  (436,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview#create-an-agent','2025-11-26 19:50:43',2,127),
  (437,'PAGE_NAVIGATION','LangChain','https://github.com/langchain-ai','2025-11-26 19:51:21',2,127),
  (438,'PAGE_NAVIGATION','langchain-ai repositories','https://github.com/orgs/langchain-ai/repositories','2025-11-26 19:51:27',2,127),
  (439,'PAGE_NAVIGATION','langchain-ai repositories','https://github.com/orgs/langchain-ai/repositories?page=2','2025-11-26 19:51:40',2,127),
  (440,'PAGE_NAVIGATION','LangChain','https://github.com/langchain-ai','2025-11-26 19:51:45',2,127),
  (441,'PAGE_NAVIGATION','Repository search results','https://github.com/search?q=topic%3Adocumentation+org%3Alangchain-ai&type=Repositories','2025-11-26 19:51:58',2,127),
  (442,'PAGE_NAVIGATION','langchain-ai repositories','https://github.com/orgs/langchain-ai/repositories?type=all','2025-11-26 19:52:02',2,127),
  (443,'PAGE_NAVIGATION','LangChain','https://github.com/langchain-ai','2025-11-26 19:52:06',2,127),
  (444,'PAGE_NAVIGATION','langchain-ai/langchain: ?? The platform for reliable agents.','https://github.com/langchain-ai/langchain','2025-11-26 19:52:14',2,127),
  (445,'TAB_SWITCH','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview#create-an-agent','2025-11-26 19:52:40',2,127);
INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (446,'TAB_SWITCH','langchain-ai/langchain: ?? The platform for reliable agents.','https://github.com/langchain-ai/langchain','2025-11-26 19:53:01',2,127),
  (447,'TAB_SWITCH','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview#create-an-agent','2025-11-26 19:53:03',2,127),
  (448,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/overview','2025-11-26 19:53:06',2,127),
  (449,'PAGE_NAVIGATION','Contributing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/code','2025-11-26 19:53:10',2,127),
  (450,'PAGE_NAVIGATION','Contributing to code - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/documentation','2025-11-26 19:53:31',2,127),
  (451,'TAB_SWITCH','langchain-ai/langchain: ?? The platform for reliable agents.','https://github.com/langchain-ai/langchain','2025-11-26 19:53:58',2,127),
  (452,'TAB_SWITCH','Contributing to documentation - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/documentation','2025-11-26 19:54:13',2,127),
  (453,'PAGE_NAVIGATION','Contributing to documentation - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/documentation','2025-11-26 19:57:57',3,127),
  (454,'PAGE_NAVIGATION','Contributing to documentation - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/comarketing','2025-11-26 19:58:51',3,127),
  (455,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*1tt9lff*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLjE3','2025-11-26 19:59:17',3,127),
  (456,'TAB_SWITCH','Co-marketing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/comarketing','2025-11-26 19:59:25',3,127),
  (457,'TAB_SWITCH','langchain-ai/langchain: ?? The platform for reliable agents.','https://github.com/langchain-ai/langchain','2025-11-26 19:59:27',3,127),
  (458,'TAB_SWITCH','Co-marketing - Docs by LangChain','https://docs.langchain.com/oss/python/contributing/comarketing','2025-11-26 19:59:27',3,127),
  (459,'PAGE_NAVIGATION','Co-marketing - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 19:59:31',3,127),
  (460,'PAGE_NAVIGATION','About','https://www.langchain.com/about?_gl=1*1h4cml1*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzL','2025-11-26 20:00:12',3,127),
  (461,'TAB_SWITCH','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 20:00:20',3,127),
  (462,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*li1e2a*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLjE3N','2025-11-26 20:00:23',3,127),
  (463,'TAB_SWITCH','About','https://www.langchain.com/about?_gl=1*1h4cml1*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzL','2025-11-26 20:01:18',3,127),
  (464,'TAB_SWITCH','LangChain Forum','https://forum.langchain.com/?_gl=1*li1e2a*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLjE3N','2025-11-26 20:01:19',3,127),
  (465,'PAGE_NAVIGATION','LangChain Support Portal','https://support.langchain.com/?_gl=1*1wblosc*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLj','2025-11-26 20:01:30',3,127),
  (466,'PAGE_NAVIGATION','LangChain Support Portal','https://support.langchain.com/?_gl=1*1wblosc*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLj','2025-11-26 20:01:30',3,127),
  (467,'PAGE_NAVIGATION','LangChain Forum','https://forum.langchain.com/?_gl=1*li1e2a*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLjE3N','2025-11-26 20:01:41',3,127),
  (468,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/?_gl=1*zzeujf*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLjE3Nj','2025-11-26 20:01:48',3,127),
  (469,'TAB_SWITCH','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 20:01:57',3,127),
  (470,'PAGE_NAVIGATION','LangChain','https://github.com/langchain-ai','2025-11-26 20:02:01',3,127),
  (471,'PAGE_NAVIGATION','LangChain','https://github.com/langchain-ai','2025-11-26 20:04:45',5,127),
  (472,'TAB_SWITCH','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 20:07:02',5,127),
  (473,'TAB_SWITCH','Home - Docs by LangChain','https://docs.langchain.com/?_gl=1*zzeujf*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLjE3Nj','2025-11-26 20:07:04',5,127),
  (474,'TAB_SWITCH','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 20:07:05',5,127),
  (475,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/messages','2025-11-26 20:07:45',5,127);
INSERT INTO `navigation` (`navigation_id`,`action`,`title`,`url`,`timestamp`,`task_id`,`collected_data_id`) VALUES
  (476,'PAGE_NAVIGATION','Messages - Docs by LangChain','https://docs.langchain.com/oss/python/langchain/overview','2025-11-26 20:08:00',5,127),
  (477,'PAGE_NAVIGATION','LangChain overview - Docs by LangChain','https://docs.langchain.com/','2025-11-26 20:08:11',5,127),
  (478,'PAGE_NAVIGATION','Home - Docs by LangChain','https://docs.langchain.com/','2025-11-26 20:08:34',5,127),
  (479,'TAB_SWITCH','Home - Docs by LangChain','https://docs.langchain.com/','2025-11-26 20:08:40',5,127),
  (480,'PAGE_NAVIGATION','Chat LangChain','https://chat.langchain.com/?_gl=1*1mrbbvk*_gcl_au*NzY4OTE1MzI0LjE3NjQxODU1Njk.*_ga*NTQ3OTY0MDUzLjE3N','2025-11-26 20:08:47',5,127),
  (481,'TAB_SWITCH','Home - Docs by LangChain','https://docs.langchain.com/','2025-11-26 20:08:52',5,127),
  (482,'PAGE_NAVIGATION','LangChain','https://github.com/langchain-ai','2025-11-26 20:09:06',5,127),
  (483,'PAGE_NAVIGATION','Packages · LangChain','https://github.com/orgs/langchain-ai/packages','2025-11-26 20:09:46',5,127),
  (484,'PAGE_NAVIGATION','Projects · langchain-ai','https://github.com/orgs/langchain-ai/projects?query=is%3Aopen','2025-11-26 20:09:53',5,127),
  (485,'PAGE_NAVIGATION','langchain-ai repositories','https://github.com/orgs/langchain-ai/repositories','2025-11-26 20:10:01',5,127),
  (486,'TAB_SWITCH','Home - Docs by LangChain','https://docs.langchain.com/','2025-11-26 20:10:37',5,127),
  (487,'TAB_SWITCH','langchain-ai repositories','https://github.com/orgs/langchain-ai/repositories','2025-11-26 20:11:39',5,127),
  (488,'PAGE_NAVIGATION','LangChain','https://github.com/langchain-ai','2025-11-26 20:11:46',5,127);
-- 283 linha(s) em `navigation`

-- `heatmap_points`: nao ha o que inserir. A tabela ja veio VAZIA no dump
-- de producao, entao os cliques dessas sessoes nao existem mais.

COMMIT;

SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;
SET SQL_MODE = @OLD_SQL_MODE;

-- ---------------------------------------------------------------------
-- CONFERENCIA (deve devolver exatamente os numeros do comentario)
-- ---------------------------------------------------------------------
SELECT e.evaluation_id, e.name, e.seco_portal,
       COUNT(DISTINCT cd.collected_data_id) AS sessoes,
       COUNT(DISTINCT dq.developer_questionnaire_id) AS questionarios,
       COUNT(DISTINCT pt.performed_task_id) AS tarefas,
       COUNT(DISTINCT a.answer_id) AS respostas,
       COUNT(DISTINCT n.navigation_id) AS navegacao
FROM evaluation e
LEFT JOIN collected_data cd ON cd.evaluation_id = e.evaluation_id
LEFT JOIN developer_questionnaire dq ON dq.collected_data_id = cd.collected_data_id
LEFT JOIN performed_task pt ON pt.collected_data_id = cd.collected_data_id
LEFT JOIN answer a ON a.collected_data_id = cd.collected_data_id
LEFT JOIN navigation n ON n.collected_data_id = cd.collected_data_id
WHERE e.evaluation_id IN (1596077, 2147077)
GROUP BY e.evaluation_id, e.name, e.seco_portal;
-- esperado:
--   1596077 pilot test                  python           2 sessoes  2 quest 14 tarefas 44 resp  36 nav
--   2147077 Lang chain portal evaluation docs.langchain  4 sessoes  4 quest 16 tarefas 52 resp 247 nav
