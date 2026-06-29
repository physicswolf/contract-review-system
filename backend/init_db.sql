CREATE TABLE IF NOT EXISTS `dimension` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name`        VARCHAR(100)    NOT NULL COMMENT '维度名称',
  `description` TEXT                     COMMENT '维度说明',
  `sort_order`  INT             NOT NULL DEFAULT 0,
  `enabled`     TINYINT         NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name` (`name`),
  KEY `idx_enabled` (`enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审查维度';

CREATE TABLE IF NOT EXISTS `audit_point` (
  `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `dim_id`         BIGINT UNSIGNED NOT NULL                  COMMENT '所属维度 ID',
  `name`           VARCHAR(200)    NOT NULL                  COMMENT '审查点名称',
  `description`    VARCHAR(500)                              COMMENT '描述',
  `instruction`    TEXT                                      COMMENT '审查说明',
  `risk_points`    JSON                                      COMMENT '[{name,highStd,lowStd,noneStd}]',
  `examples`       JSON                                      COMMENT '审查示例列表',
  `default_result` JSON                                      COMMENT '默认结论',
  `enabled`        TINYINT         NOT NULL DEFAULT 1        COMMENT '1启用 0停用',
  `sort_order`     INT             NOT NULL DEFAULT 0,
  `created_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at`     DATETIME                 DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_dim` (`dim_id`, `deleted_at`, `enabled`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='审查点';

CREATE TABLE IF NOT EXISTS `contract_type` (
  `id`          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `code`        VARCHAR(50)              COMMENT '类型编码',
  `name`        VARCHAR(100)    NOT NULL COMMENT '合同类型名称',
  `stance`      VARCHAR(50)     NOT NULL COMMENT '立场',
  `description` TEXT                     COMMENT '合同描述',
  `keywords`    JSON                     COMMENT '识别关键词列表',
  `enabled`     TINYINT         NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
  `created_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at`  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `deleted_at`  DATETIME                 DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_name_stance` (`name`, `stance`),
  KEY `idx_enabled` (`enabled`, `deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同类型';

CREATE TABLE IF NOT EXISTS `contract_type_audit_point` (
  `id`               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  `contract_type_id` BIGINT UNSIGNED NOT NULL,
  `audit_point_id`   BIGINT UNSIGNED NOT NULL,
  `enabled`          TINYINT         NOT NULL DEFAULT 1 COMMENT '该合同类型下是否启用此审查点',
  `sort_order`       INT             NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_ct_ap` (`contract_type_id`, `audit_point_id`),
  KEY `idx_ct` (`contract_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='合同类型-审查点关联';
