CREATE TABLE IF NOT EXISTS `user` (
    `id`         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    `account`    VARCHAR(128) NOT NULL COMMENT '登录账号/邮箱',
    `password`   VARCHAR(256) NOT NULL COMMENT 'bcrypt hash',
    `name`       VARCHAR(100) NOT NULL COMMENT '显示名称',
    `company`    VARCHAR(200) NOT NULL DEFAULT '' COMMENT '公司名称',
    `role`       VARCHAR(50)  NOT NULL DEFAULT '企业管理员' COMMENT '角色',
    `phone`      VARCHAR(20)  NOT NULL DEFAULT '' COMMENT '手机号',
    `email`      VARCHAR(128) NOT NULL DEFAULT '' COMMENT '邮箱',
    `status`     TINYINT      NOT NULL DEFAULT 1 COMMENT '1启用 0停用',
    `created_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `updated_at` DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_account` (`account`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='系统用户';
