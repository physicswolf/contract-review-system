CREATE TABLE IF NOT EXISTS `dimension` (
    `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `name`       VARCHAR(100) NOT NULL COMMENT '维度名称',
    `desc`       TEXT COMMENT '维度说明',
    `sort_order` INT NOT NULL DEFAULT 0,
    `status`     VARCHAR(20) NOT NULL DEFAULT '已启用' COMMENT '已启用/已停用',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审查维度';

CREATE TABLE IF NOT EXISTS `audit_point` (
    `id`              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `dim_id`          BIGINT UNSIGNED NOT NULL COMMENT '所属维度ID',
    `name`            VARCHAR(200) NOT NULL COMMENT '审查点名称',
    `category`        VARCHAR(50)  NOT NULL DEFAULT '' COMMENT '后果类别',
    `desc`            VARCHAR(500) DEFAULT '' COMMENT '描述',
    `instruction`     TEXT COMMENT '审查说明',
    `risk_points`     JSON COMMENT '风险点列表',
    `examples`        JSON COMMENT '审查示例列表',
    `default_result`  JSON COMMENT '默认结论',
    `default_checked` TINYINT NOT NULL DEFAULT 1 COMMENT '默认勾选',
    `status`          VARCHAR(20) NOT NULL DEFAULT '已启用' COMMENT '已启用/已停用',
    `sort_order`      INT NOT NULL DEFAULT 0,
    `created_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at`      DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`),
    KEY `idx_dim` (`dim_id`, `deleted_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审查点';

CREATE TABLE IF NOT EXISTS `contract_type` (
    `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `code`           VARCHAR(50) COMMENT '类型编码',
    `name`           VARCHAR(100) NOT NULL COMMENT '合同类型名称',
    `stance`         VARCHAR(50)  NOT NULL DEFAULT '' COMMENT '立场',
    `desc`           TEXT COMMENT '合同描述',
    `keywords`       JSON COMMENT '识别关键词列表',
    `related_points` INT NOT NULL DEFAULT 0 COMMENT '关联审查点数量',
    `status`         VARCHAR(20) NOT NULL DEFAULT '已启用' COMMENT '已启用/已停用',
    `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    `deleted_at`     DATETIME DEFAULT NULL,
    PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='合同类型';

CREATE TABLE IF NOT EXISTS `contract_type_audit_point` (
    `id`               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `contract_type_id` BIGINT UNSIGNED NOT NULL,
    `audit_point_id`   BIGINT UNSIGNED NOT NULL,
    `enabled`          TINYINT NOT NULL DEFAULT 1 COMMENT '该合同类型下是否启用',
    `sort_order`       INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_ct_ap` (`contract_type_id`, `audit_point_id`),
    KEY `idx_ct` (`contract_type_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='合同类型-审查点关联';
