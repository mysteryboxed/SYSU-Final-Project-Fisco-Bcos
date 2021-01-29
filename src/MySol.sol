/*
    组别：王广烁 18340165
        孙新梦 18340149
        张洪宾 18340208
    描述：智能合约的设计
    部署：在fisco-bcos控制台部署，参考上次实验
*/
pragma solidity ^0.4.24;
pragma experimental ABIEncoderV2;

import "./Table.sol";

contract Bank
{
    //设置event，可以方便看到函数的调用过程，方便调试
    event RegisterEvent(int256 ret, string account, int256 asset_value);
    event TransferEvent(int256 ret, string from_account, string to_account, int256 amount);
    event AddTransactionEvent(int256 ret, string id, string acc1, string acc2, int256 money);
    event UpdateTransactionEvent(int256 ret, string id, int256 money);

    //初始函数
    constructor() public
    {
        createTable();
    }


    //下面这些基于table.sol以及官方文档编写。
    function createTable() private{
        TableFactory tf = TableFactory(0x1001);
        // 资产管理表, key : account, field : asset_value
        // |   资产账户(主键)      |     信用额度       |
        // |-------------------- |-------------------|
        // |        account      |    asset_value    |
        // |---------------------|-------------------|
        //
        // 创建表
        tf.createTable("t_asset", "account", "asset_value");
        // 交易记录表, key: id, field: acc1, acc2, money, status
        // | 交易单号(key) | 债主 | 借债人 | 债务金额 |   状态   |
        // |-------------|------|-------|---------|---------|
        // |     id      | acc1 | acc2  |  money  | status  |
        // |-------------|------|-------|---------|---------|
        tf.createTable("t_transaction", "id","acc1, acc2, money, status");
    }

    // 返回t_asset，打开合约表格
    function openAssetTable() private returns(Table) {
        TableFactory tf = TableFactory(0x1001);
        Table table = tf.openTable("t_asset");
        return table;
    }

    // 返回t_transaction，打开交易表格
    function openTransactionTable() private returns(Table) {
        TableFactory tf = TableFactory(0x1001);
        Table table = tf.openTable("t_transaction");
        return table;
    }


    //下面是主要函数
    
    /*
        函数：select，查询金额功能
        输入：account：资产账户
        返回：结果代号和金额
    */
    function select(string account) public constant returns(int256, int256) {
        Table table = openAssetTable(); // 打开表格
        Entries entries = table.select(account, table.newCondition());// 查询额度
        int256 asset_value = 0;
        if (0 == uint256(entries.size())){ //查找失败 
            return (-1, asset_value);
        }
        else{
            Entry entry = entries.get(0);
            return (0, int256(entry.getInt("asset_value")));
        }
    }

    /*
        select_transaction函数，查询交易
        输入：交易ID
        返回值：结果代号
    */
    function select_transaction(string id) public constant returns(int256[], bytes32[]) {
        Table table = openTransactionTable();// 打开交易表格
        Entries entries = table.select(id, table.newCondition());// 查询交易
        int256[] memory int_list = new int256[](3);   
        bytes32[] memory str_list = new bytes32[](2);   
        if (0 == uint256(entries.size())){ //查找失败
            int_list[0] = -1;
            return (int_list, str_list);
        }
        else{//返回第一个
            Entry entry = entries.get(0);
            int_list[1] = entry.getInt("money");
            int_list[2] = entry.getInt("status");
            str_list[0] = entry.getBytes32("acc1");
            str_list[1] = entry.getBytes32("acc2");
            return (int_list, str_list);
        }
    }

    /*
        函数：register，注册账户的金额
        输入 ： 账户名，金额
        返回：结果代号
    */
    function register(string account, int256 asset_value) public returns(int256){
        int256 ret_code = 0;//返回值
        int256 ret = 0;
        int256 temp_asset_value = 0;
        (ret, temp_asset_value) = select(account); // 查询账户是否存在
        if(ret != 0) 
        {
            Table table = openAssetTable();
            Entry entry = table.newEntry();//新建表
            entry.set("account", account);//初始化
            entry.set("asset_value", int256(asset_value));
            int count = table.insert(account, entry);// 插入
            if (count == 1) {
                ret_code = 0;
            }
            else {  // 失败? 无权限或者其他错误
                ret_code = -2;
            }
        }
        else {// 账户已存在
            ret_code = -1;
        }
        emit RegisterEvent(ret_code, account, asset_value);
        return ret_code;
    }

    /*
        函数：addTransaction，添加交易记录:欠条号为id，acc1借给acc2money数值的钱 
        输入 ： 交易ID，债主账户名，欠款人账户名，金额
        返回：结果代号
    */
    function addTransaction(string id, string acc1, string acc2, int256 money) public returns(int256){
        int256 ret_code = 0;//返回
        int256 ret = 0;
        bytes32[] memory str_list = new bytes32[](2);
        int256[] memory int_list = new int256[](3);
        (int_list, str_list) = select_transaction(id);
        if(int_list[0] != int256(0)){   //可以交易
            Table table = openTransactionTable();
            Entry entry0 = table.newEntry();
            entry0.set("id", id);
            entry0.set("acc1", acc1);
            entry0.set("acc2", acc2);
            entry0.set("money", int256(money));
            entry0.set("status", int256(money));
            int count = table.insert(id, entry0);
            if (count == 1) { // 将欠款人的信用额度转移一部分给债主
                ret = transfer(acc2,acc1,money);
                if(ret != 0) {
                    ret_code = -3;
                } else {
                    ret_code = 0;
                }
            } else {
                ret_code = -2;
            }
        }
        else {
            ret_code = -1;
        }
        emit AddTransactionEvent(ret_code, id, acc1, acc2, money);
        return ret_code;
    }

    /*
        函数：updateTransaction，支付欠款（少于初始金额）
        输入： 交易ID，还款金额
        返回：结果代号
    */
    
    function updateTransaction(string id, int256 money) public returns(int256, string[]){
        int256 ret_code = 0;
        bytes32[] memory str_list = new bytes32[](2);
        int256[] memory int_list = new int256[](3);
        string[] memory acc_list = new string[](2);
        (int_list, str_list) = select_transaction(id); 
        acc_list[0] = byte32ToString(str_list[0]);
        acc_list[1] = byte32ToString(str_list[1]);
        if(int_list[0] == 0) 
        { 
            if(int_list[2] < money){//还款金额大于欠条金额
                ret_code = -2;
                emit UpdateTransactionEvent(ret_code, id, money);//调用事件
                return (ret_code, acc_list);
            }
            Table table = openTransactionTable();//更新状态
            Entry entry0 = table.newEntry();//新建交易表项
            entry0.set("id", id);
            entry0.set("acc1", byte32ToString(str_list[0]));
            entry0.set("acc2", byte32ToString(str_list[1]));
            entry0.set("money", int_list[1]);
            entry0.set("status", (int_list[2] - money));
            int count = table.update(id, entry0, table.newCondition());
            if(count != 1) {
                ret_code = -3;
                emit UpdateTransactionEvent(ret_code, id, money);
                return (ret_code,acc_list);
            }
            int256 temp = transfer(byte32ToString(str_list[0]),byte32ToString(str_list[1]),money);
            if(temp != 0){
                ret_code = -4 * 10 + temp;
                emit UpdateTransactionEvent(ret_code, id, money);
                return (ret_code,acc_list);
            }

            ret_code = 0;
      
        }
        else { // 交易ID不存在，没有这个交易
            ret_code = -1;
        }
        emit UpdateTransactionEvent(ret_code, id, money);

        return (ret_code,acc_list);
    }

    /*
        函数：transfer，金额转移
        输入 ： 转移资产账户名,接收资产账户名,转移金额
        返回：结果代号
    */
    function transfer(string from_account, string to_account, int256 amount) public returns(int256) {
        int ret_code = 0;
        int256 ret = 0;
        int256 from_asset_value = 0;
        int256 to_asset_value = 0;
        (ret, from_asset_value) = select(from_account);
        if(ret != 0) {// 转移账户不存在
            ret_code = -1;
            emit TransferEvent(ret_code, from_account, to_account, amount);//通报事件
            return ret_code;

        }
        (ret, to_asset_value) = select(to_account);
        if(ret != 0) //不存在
        {
            ret_code = -2;
            emit TransferEvent(ret_code, from_account, to_account, amount);
            return ret_code;
        }

        if(from_asset_value < amount) { // 金额不足
            ret_code = -3;
            emit TransferEvent(ret_code, from_account, to_account, amount);
            return ret_code;
        } 

        if (to_asset_value + amount < to_asset_value) {
            ret_code = -4;
            emit TransferEvent(ret_code, from_account, to_account, amount);
            return ret_code;
        }
        Table table = openAssetTable();
        Entry entry0 = table.newEntry();
        entry0.set("account", from_account);
        entry0.set("asset_value", int256(from_asset_value - amount));
        int count = table.update(from_account, entry0, table.newCondition());
        if(count != 1) {
            ret_code = -5;
            emit TransferEvent(ret_code, from_account, to_account, amount);
            return ret_code;
        }

        Entry entry1 = table.newEntry();
        entry1.set("account", to_account);
        entry1.set("asset_value", int256(to_asset_value + amount));
        table.update(to_account, entry1, table.newCondition());
        emit TransferEvent(ret_code, from_account, to_account, amount);
        return ret_code;
    }

}

    /*
        函数：splitTransaction，债权转移(少于欠条金额)
        输入 ： 需要拆分的欠条ID，新创建的欠条的ID，新创建欠条的债主， 欠条拆分的金额
        返回 :结果代号
    */
    function splitTransaction(string old_id, string new_id, string acc, int256 money) public returns(int256) {
        int256 ret_code = 0;
        int256 ret = 0;
        int temp = 0;
        bytes32[] memory str_list = new bytes32[](2);
        int256[] memory int_list = new int256[](3);
        string[] memory acc_list = new string[](2);
        (int_list, str_list) = select_transaction(old_id);
        if(int_list[0] == 0) {
            (ret, temp) = select(acc);
            if(ret != 0) {
                ret_code = -5;
                emit SplitTransactionEvent(ret_code, old_id, new_id, acc, money);
                return ret_code;
            }

            if(int_list[2] < money){    //大于欠条余额
                ret_code = -2;
                emit SplitTransactionEvent(ret_code, old_id, new_id, acc, money);
                return ret_code;
            }
            (ret,acc_list) = updateTransaction(old_id, money);
            if (ret != 0) {
                ret_code = -4;
                emit SplitTransactionEvent(ret_code, old_id, new_id, acc, money);
                return ret_code;
            }
            ret = addTransaction(new_id, acc, byte32ToString(str_list[1]), money);
            if (ret != 0) {
                ret_code = -3;
                emit SplitTransactionEvent(ret_code, old_id, new_id, acc, money);
                return ret_code;
            }

        } else {    // 欠条id不存在
            ret_code = -1;
        }
        emit SplitTransactionEvent(ret_code, old_id, new_id, acc, money);
        return ret_code;
    }