CREATE TABLE IF NOT EXISTS `audit_task` (
    `id`                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `contract_id`        BIGINT UNSIGNED NOT NULL COMMENT '关联合同ID',
    `contract_type_id`   BIGINT UNSIGNED COMMENT '合同类型ID',
    `stance`             VARCHAR(50) NOT NULL DEFAULT '甲方' COMMENT '审核立场',
    `status`             VARCHAR(20) NOT NULL DEFAULT 'queued' COMMENT 'queued/running/succeeded/failed',
    `total_risk_count`   INT NOT NULL DEFAULT 0,
    `major_risk_count`   INT NOT NULL DEFAULT 0,
    `general_risk_count` INT NOT NULL DEFAULT 0,
    `created_at`         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at`         DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_contract` (`contract_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审核任务';

CREATE TABLE IF NOT EXISTS `audit_result_item` (
    `id`             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `task_id`        BIGINT UNSIGNED NOT NULL COMMENT '审核任务ID',
    `dim_id`         BIGINT UNSIGNED NOT NULL COMMENT '维度ID',
    `dim_name`       VARCHAR(100) NOT NULL COMMENT '维度名称',
    `audit_point_id` BIGINT UNSIGNED COMMENT '审查点ID',
    `title`          VARCHAR(200) NOT NULL COMMENT '风险点标题',
    `risk_level`     TINYINT NOT NULL COMMENT '1=重大风险 2=一般风险',
    `risk_summary`   TEXT COMMENT '风险说明',
    `risk_analysis`  TEXT COMMENT '风险分析',
    `modify_example` TEXT COMMENT '修改示例',
    `clause_name`    VARCHAR(200) COMMENT '所属条款',
    `hit_text`       TEXT COMMENT '命中原文',
    `display`        TINYINT NOT NULL DEFAULT 1 COMMENT '1显示 0用户忽略',
    `sort_order`     INT NOT NULL DEFAULT 0,
    `created_at`     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    KEY `idx_task_dim` (`task_id`, `dim_id`, `display`),
    KEY `idx_task_level` (`task_id`, `risk_level`, `display`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审核结果明细';

CREATE TABLE IF NOT EXISTS `audit_dimension_stat` (
    `id`            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `task_id`       BIGINT UNSIGNED NOT NULL,
    `dim_id`        BIGINT UNSIGNED NOT NULL,
    `dim_name`      VARCHAR(100) NOT NULL COMMENT '维度名称',
    `total_count`   INT NOT NULL DEFAULT 0,
    `major_count`   INT NOT NULL DEFAULT 0,
    `general_count` INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_task_dim` (`task_id`, `dim_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='审核维度统计';
