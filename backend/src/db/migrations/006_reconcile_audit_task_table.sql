ALTER TABLE audit_task ADD COLUMN `contract_id` BIGINT UNSIGNED NULL COMMENT '关联合同ID' AFTER `id`;
ALTER TABLE audit_task ADD COLUMN `contract_type_id` BIGINT UNSIGNED NULL COMMENT '合同类型ID' AFTER `contract_id`;
ALTER TABLE audit_task ADD COLUMN `stance` VARCHAR(50) NOT NULL DEFAULT '甲方' COMMENT '审核立场' AFTER `contract_type_id`;
ALTER TABLE audit_task ADD INDEX `idx_contract` (`contract_id`);
