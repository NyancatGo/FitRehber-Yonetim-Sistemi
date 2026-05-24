DROP PROCEDURE IF EXISTS sp_ProfilBanGuncelle;

DELIMITER $$
CREATE PROCEDURE sp_ProfilBanGuncelle(
    IN p_id BIGINT,
    IN p_is_banned TINYINT(1),
    IN p_timeout_until DATETIME(6)
)
BEGIN
    UPDATE profiller
       SET is_banned = p_is_banned,
           timeout_until = p_timeout_until
     WHERE id = p_id;
END$$
DELIMITER ;

