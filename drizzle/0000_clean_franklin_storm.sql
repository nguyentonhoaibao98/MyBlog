CREATE TABLE `attempts` (
	`id` text PRIMARY KEY NOT NULL,
	`count` integer NOT NULL,
	`until` integer NOT NULL
);
--> statement-breakpoint
CREATE TABLE `topics` (
	`id` text PRIMARY KEY NOT NULL,
	`title` text NOT NULL,
	`summary` text NOT NULL,
	`category` text NOT NULL,
	`content` text DEFAULT '' NOT NULL,
	`public` integer DEFAULT 0 NOT NULL,
	`file` text,
	`filename` text,
	`created` text NOT NULL
);
